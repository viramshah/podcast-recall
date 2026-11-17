"""The real GoogleYouTubeClient, driven by a fake `service` object and stand-ins for Google's
exception classes (the Google libraries are not needed to run these tests)."""

from __future__ import annotations

import json
import sys
import types
import unittest
from typing import ClassVar

from podcast_recall.errors import ApiError, NotSignedIn, QuotaExceeded, TransientError
from podcast_recall.youtube_client import GoogleYouTubeClient, _classify


class FakeHttpError(Exception):
    def __init__(self, status: int, reason: str = "") -> None:
        super().__init__(f"HTTP {status}")
        self.resp = types.SimpleNamespace(status=status)
        self.content = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()


class FakeRefreshError(Exception):
    pass


class FakeTransportError(Exception):
    pass


class WithFakeGoogleModules(unittest.TestCase):
    """Install stand-ins for googleapiclient.errors and google.auth.exceptions."""

    MODULES: ClassVar[dict[str, types.ModuleType]] = {
        "googleapiclient": types.ModuleType("googleapiclient"),
        "googleapiclient.errors": types.ModuleType("googleapiclient.errors"),
        "google": types.ModuleType("google"),
        "google.auth": types.ModuleType("google.auth"),
        "google.auth.exceptions": types.ModuleType("google.auth.exceptions"),
    }

    def setUp(self) -> None:
        self.MODULES["googleapiclient.errors"].HttpError = FakeHttpError
        self.MODULES["google.auth.exceptions"].RefreshError = FakeRefreshError
        self.MODULES["google.auth.exceptions"].TransportError = FakeTransportError
        self._saved = {name: sys.modules.get(name) for name in self.MODULES}
        sys.modules.update(self.MODULES)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        for name, module in self._saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class Classification(WithFakeGoogleModules):
    def test_mapping(self):
        self.assertIsInstance(_classify(FakeRefreshError("x")), NotSignedIn)
        self.assertIsInstance(_classify(FakeHttpError(401)), NotSignedIn)
        self.assertIsInstance(_classify(FakeHttpError(403, "quotaExceeded")), QuotaExceeded)
        self.assertIsInstance(_classify(FakeHttpError(403, "dailyLimitExceeded")), QuotaExceeded)
        self.assertIsInstance(_classify(FakeHttpError(403, "rateLimitExceeded")), TransientError)
        self.assertIsInstance(_classify(FakeHttpError(429)), TransientError)
        self.assertIsInstance(_classify(FakeHttpError(503)), TransientError)
        self.assertIsInstance(_classify(FakeTransportError()), TransientError)
        self.assertIsInstance(_classify(TimeoutError()), TransientError)
        self.assertIsInstance(_classify(OSError("reset")), TransientError)
        not_transient = _classify(FakeHttpError(404, "playlistNotFound"))
        self.assertIsInstance(not_transient, ApiError)
        self.assertNotIsInstance(not_transient, TransientError)
        self.assertIsInstance(_classify(ValueError("weird")), ApiError)

    def test_messages_never_contain_urls_or_tokens(self):
        err = FakeHttpError(400, "badRequest")
        err.uri = "https://www.googleapis.com/youtube/v3/videos?access_token=ya29.SECRET"
        self.assertNotIn("ya29", str(_classify(err)))
        self.assertNotIn("http", str(_classify(err)).lower().replace("http 400", ""))


class FakeRequest:
    def __init__(self, outcomes):
        self.outcomes = outcomes

    def execute(self):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeResource:
    """Behaves like `service.something()`: `.list(**kwargs)` returns a request."""

    def __init__(self, outcomes_by_call):
        self.outcomes = outcomes_by_call
        self.requests: list[dict] = []

    def list(self, **kwargs):
        self.requests.append(kwargs)
        return FakeRequest(self.outcomes)


class FakeService:
    def __init__(self, **resources):
        self.resources = resources

    def __getattr__(self, name):
        if name in self.resources:
            return lambda: self.resources[name]
        raise AttributeError(name)


def client_with(**resources):
    sleeps: list[float] = []
    client = GoogleYouTubeClient(FakeService(**resources), sleep=sleeps.append, rng=lambda: 0.5)
    client.sleeps = sleeps  # type: ignore[attr-defined]
    return client


class Calls(WithFakeGoogleModules):
    def test_subscriptions_follow_page_tokens_and_count_each_call(self):
        pages = [
            {"items": [{"snippet": {"title": "A", "resourceId": {"channelId": "UC1"}}}],
             "nextPageToken": "t2"},
            {"items": [{"snippet": {"title": "B", "resourceId": {"channelId": "UC2"}}}]},
        ]
        resource = FakeResource(pages)
        client = client_with(subscriptions=resource)
        subs = client.list_subscriptions()
        self.assertEqual([s.channel_id for s in subs], ["UC1", "UC2"])
        self.assertEqual(client.calls, {"subscriptions.list": 2})
        self.assertEqual(client.units, 2)
        self.assertEqual(resource.requests[1]["pageToken"], "t2")
        self.assertTrue(all(r["mine"] is True for r in resource.requests))

    def test_playlist_items_stop_at_max_items(self):
        page = {"items": [{"contentDetails": {"videoId": f"v{i}"}} for i in range(50)],
                "nextPageToken": "more"}
        resource = FakeResource([page, page])
        client = client_with(playlistItems=resource)
        ids = client.list_playlist_video_ids("UU1", max_items=50)
        self.assertEqual(len(ids), 50)
        self.assertEqual(client.calls, {"playlistItems.list": 1})  # did not ask for a second page
        self.assertEqual(resource.requests[0]["maxResults"], 50)

    def test_temporary_errors_are_retried_and_counted(self):
        resource = FakeResource([FakeHttpError(503), FakeHttpError(503), {"items": [
            {"id": "v1", "snippet": {"title": "T", "channelId": "UC1", "channelTitle": "C",
                                      "publishedAt": "2026-01-01T00:00:00Z",
                                      "description": "d" * 900, "liveBroadcastContent": "upcoming"},
             "contentDetails": {"duration": "PT1H2M3S"}}]}])
        client = client_with(videos=resource)
        videos = client.get_videos(["v1", "v2"])
        self.assertEqual(client.calls, {"videos.list": 3})  # every attempt costs quota
        self.assertEqual(client.sleeps, [1, 2])
        self.assertEqual(videos[0].duration_s, 3723)
        self.assertEqual(len(videos[0].description), 500)
        self.assertTrue(videos[0].is_live_or_upcoming)
        self.assertEqual(resource.requests[0]["id"], "v1,v2")
        self.assertNotIn("maxResults", resource.requests[0])

    def test_quota_exceeded_is_not_retried(self):
        client = client_with(videos=FakeResource([FakeHttpError(403, "quotaExceeded")]))
        with self.assertRaises(QuotaExceeded):
            client.get_videos(["v1"])
        self.assertEqual(client.calls, {"videos.list": 1})
        self.assertEqual(client.sleeps, [])

    def test_my_channel_reads_the_likes_playlist(self):
        resource = FakeResource([{"items": [{"id": "UCme", "snippet": {"title": "Me"},
                                              "contentDetails": {"relatedPlaylists": {"likes": "LL1"}}}]}])
        me = client_with(channels=resource).my_channel()
        self.assertEqual((me.channel_id, me.title, me.likes_playlist_id), ("UCme", "Me", "LL1"))
        self.assertTrue(resource.requests[0]["mine"])

    def test_my_channel_without_a_channel_is_an_error(self):
        with self.assertRaises(ApiError):
            client_with(channels=FakeResource([{"items": []}])).my_channel()

    def test_batches_larger_than_50_are_refused(self):
        client = client_with(videos=FakeResource([]))
        with self.assertRaises(ValueError):
            client.get_videos([f"v{i}" for i in range(51)])
