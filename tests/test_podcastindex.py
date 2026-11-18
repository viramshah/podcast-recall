"""The Podcast Index client with a fake network: signing, parsing, errors, retries and credentials."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from podcast_recall import logging_setup, podcastindex
from podcast_recall.errors import ApiError, ConfigError
from podcast_recall.podcastindex import Credentials, PodcastIndexClient

CREDS = Credentials("KEYVALUE123", "SECRETVALUE456")


class FakeTransport:
    """Returns the queued responses in order and records every request."""

    def __init__(self, *responses) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict, timeout: float):
        self.requests.append((url, headers))
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        status, body = item
        return status, body if isinstance(body, bytes) else json.dumps(body).encode()


def client_with(*responses, **kwargs) -> tuple[PodcastIndexClient, FakeTransport, list[float]]:
    transport = FakeTransport(*responses)
    sleeps: list[float] = []
    client = PodcastIndexClient(
        CREDS, transport=transport, sleep=sleeps.append, rng=lambda: 0.5, clock=lambda: 1_700_000_000,
        pause=kwargs.pop("pause", 0), **kwargs,
    )
    return client, transport, sleeps


EPISODES = {"status": "true", "items": [
    {"id": 11, "feedId": 5, "guid": "g1", "title": "One", "datePublished": 1_700_000_100, "duration": 3600,
     "enclosureUrl": "https://a/1.mp3", "enclosureType": "audio/mpeg",
     "transcriptUrl": "https://a/1.vtt", "transcripts": [{"url": "https://a/1.vtt", "type": "text/vtt"}],
     "link": "https://a/1"},
    {"id": 12, "feedId": 5, "guid": "g2", "title": "Two", "datePublished": 1_700_000_000, "duration": "01:02:03"},
    {"id": 13, "feedId": 5, "guid": "g3", "title": "Three", "datePublished": 1_699_999_000, "duration": 0},
]}


class Requests(unittest.TestCase):
    def test_requests_are_signed_with_the_documented_recipe(self):
        client, transport, _ = client_with((200, EPISODES))
        client.episodes(5)
        url, headers = transport.requests[0]
        self.assertEqual(headers["X-Auth-Key"], "KEYVALUE123")
        self.assertEqual(headers["X-Auth-Date"], "1700000000")
        expected = hashlib.sha1(b"KEYVALUE123SECRETVALUE4561700000000").hexdigest()
        self.assertEqual(headers["Authorization"], expected)
        self.assertEqual(urlparse(url).path, "/api/1.0/episodes/byfeedid")

    def test_secrets_are_never_in_the_url(self):
        client, transport, _ = client_with((200, EPISODES))
        client.episodes(5)
        self.assertNotIn("SECRETVALUE", transport.requests[0][0])
        self.assertNotIn("KEYVALUE", transport.requests[0][0])

    def test_episodes_asks_for_the_whole_feed_the_first_time_and_since_later(self):
        client, transport, _ = client_with((200, EPISODES))
        client.episodes(5)
        client.episodes(5, since=1_700_000_000)
        first = parse_qs(urlparse(transport.requests[0][0]).query)
        later = parse_qs(urlparse(transport.requests[1][0]).query)
        self.assertEqual((first["id"], first["max"]), (["5"], ["1000"]))
        self.assertNotIn("since", first)
        self.assertEqual(later["since"], ["1700000000"])

    def test_calls_are_counted_by_endpoint(self):
        client, _, _ = client_with((200, EPISODES))
        client.episodes(5)
        client.episodes(5)
        self.assertEqual(client.calls, {"episodes/byfeedid": 2})
        self.assertEqual(client.total_calls, 2)

    def test_a_pause_follows_each_call(self):
        client, _, sleeps = client_with((200, EPISODES), pause=0.2)
        client.episodes(5)
        self.assertEqual(sleeps, [0.2])


class Parsing(unittest.TestCase):
    def test_episodes_are_parsed_including_transcript_links(self):
        client, _, _ = client_with((200, EPISODES))
        first, second, third = client.episodes(5)
        self.assertEqual((first.episode_id, first.feed_id, first.guid, first.title), (11, 5, "g1", "One"))
        self.assertEqual(first.duration_s, 3600)
        self.assertEqual(first.transcript_url, "https://a/1.vtt")
        self.assertEqual(first.transcripts[0]["type"], "text/vtt")
        self.assertEqual(first.audio_url, "https://a/1.mp3")
        self.assertEqual(second.duration_s, 3723)  # "01:02:03" text
        self.assertIsNone(second.transcript_url)
        self.assertIsNone(third.duration_s)  # 0 means unknown

    def test_a_transcript_link_is_found_in_the_transcripts_list_too(self):
        body = {"status": "true", "items": [{"id": 1, "title": "T", "transcripts": [{"url": "https://x/t.srt"}]}]}
        client, _, _ = client_with((200, body))
        self.assertEqual(client.episodes(9)[0].transcript_url, "https://x/t.srt")

    def test_duration_formats(self):
        parse = podcastindex.parse_duration
        self.assertEqual(parse(5235), 5235)
        self.assertEqual(parse(5235.0), 5235)
        self.assertEqual(parse("5235"), 5235)
        self.assertEqual(parse("1:02:03"), 3723)
        self.assertEqual(parse("45:10"), 2710)
        for unknown in (0, "0", "00:00:00", None, "soon", "1:xx", True, -5):
            self.assertIsNone(parse(unknown), unknown)

    def test_feed_lookup_and_search(self):
        feed = {"id": 5487204, "title": "Lenny's Podcast", "url": "https://f/x.rss", "author": "Lenny",
                "language": "en", "episodeCount": 370, "lastUpdateTime": 1_794_941_019}
        client, _, _ = client_with((200, {"status": "true", "feed": feed}))
        found = client.feed_by_url("https://f/x.rss")
        self.assertEqual((found.feed_id, found.title, found.episode_count), (5487204, "Lenny's Podcast", 370))
        client, _, _ = client_with((200, {"status": "true", "feeds": [feed, feed]}))
        self.assertEqual(len(client.search_feeds("Lenny")), 2)

    def test_an_unknown_feed_is_none(self):
        client, _, _ = client_with((200, {"status": "true", "feed": []}))
        self.assertIsNone(client.feed_by_url("https://nowhere"))


class Failures(unittest.TestCase):
    def test_bad_credentials_are_a_config_error_and_are_not_retried(self):
        for status in (401, 403):
            client, transport, sleeps = client_with((status, {"status": "false"}))
            with self.assertRaises(ConfigError):
                client.episodes(5)
            self.assertEqual((len(transport.requests), sleeps), (1, []))

    def test_temporary_errors_are_retried_with_growing_delays(self):
        client, transport, sleeps = client_with((503, b""), (429, b""), (200, EPISODES))
        self.assertEqual(len(client.episodes(5)), 3)
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(sleeps, [1, 2])

    def test_network_errors_are_retried_then_become_an_api_error(self):
        client, transport, sleeps = client_with(OSError("reset"))
        with self.assertRaises(ApiError):
            client.episodes(5)
        self.assertEqual(len(transport.requests), 6)
        self.assertEqual(sleeps, [1, 2, 4, 8, 16])

    def test_other_http_errors_are_api_errors_and_are_not_retried(self):
        client, transport, _ = client_with((404, b""))
        with self.assertRaises(ApiError):
            client.episodes(5)
        self.assertEqual(len(transport.requests), 1)

    def test_an_error_body_is_an_api_error(self):
        client, _, _ = client_with((200, {"status": "false", "description": "Invalid feed id"}))
        with self.assertRaisesRegex(ApiError, "Invalid feed id"):
            client.episodes(5)

    def test_unreadable_responses_are_api_errors(self):
        for body in (b"<html>", b"[1, 2]"):
            client, _, _ = client_with((200, body))
            with self.assertRaises(ApiError):
                client.episodes(5)

    def test_error_messages_never_contain_the_credentials(self):
        client, _, _ = client_with((401, b""))
        try:
            client.episodes(5)
        except ConfigError as exc:
            self.assertNotIn("KEYVALUE", str(exc))
            self.assertNotIn("SECRETVALUE", str(exc))


class CredentialLoading(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "podcastindex.env"

    def write(self, text: str, mode: int = 0o600) -> None:
        self.path.write_text(text, encoding="utf-8")
        os.chmod(self.path, mode)

    def test_the_file_format_from_week_zero_is_read(self):
        self.write("export PODCASTINDEX_KEY=abc\nexport PODCASTINDEX_SECRET='def'\n# comment\n")
        creds = podcastindex.load_credentials(env={}, env_file=self.path)
        self.assertEqual(creds, Credentials("abc", "def"))

    def test_environment_variables_win_over_the_file(self):
        self.write("export PODCASTINDEX_KEY=filekey\nexport PODCASTINDEX_SECRET=filesecret\n")
        creds = podcastindex.load_credentials(
            env={"PODCASTINDEX_KEY": "envkey", "PODCASTINDEX_SECRET": "envsecret"}, env_file=self.path)
        self.assertEqual(creds, Credentials("envkey", "envsecret"))

    def test_the_file_fills_in_what_the_environment_lacks(self):
        self.write("export PODCASTINDEX_SECRET=filesecret\n")
        creds = podcastindex.load_credentials(env={"PODCASTINDEX_KEY": "envkey"}, env_file=self.path)
        self.assertEqual(creds, Credentials("envkey", "filesecret"))

    def test_a_file_readable_by_others_is_refused(self):
        for mode in (0o644, 0o640, 0o604):
            self.write("export PODCASTINDEX_KEY=abc\nexport PODCASTINDEX_SECRET=def\n", mode)
            with self.assertRaisesRegex(ConfigError, "chmod 600"):
                podcastindex.load_credentials(env={}, env_file=self.path)

    def test_missing_credentials_are_explained(self):
        with self.assertRaisesRegex(ConfigError, "PODCASTINDEX_KEY"):
            podcastindex.load_credentials(env={}, env_file=self.path)

    def test_a_file_with_only_one_value_is_not_enough(self):
        self.write("export PODCASTINDEX_KEY=abc\n")
        with self.assertRaises(ConfigError):
            podcastindex.load_credentials(env={}, env_file=self.path)


class Redaction(unittest.TestCase):
    def test_podcast_index_secrets_are_removed_from_log_text(self):
        for text in (
            "request headers X-Auth-Key: KEYVALUE123 sent",
            "export PODCASTINDEX_SECRET=SECRETVALUE456",
            "PODCASTINDEX_KEY='KEYVALUE123'",
            "Authorization: 0123456789abcdef0123456789abcdef01234567",
        ):
            cleaned = logging_setup.redact(text)
            self.assertNotIn("KEYVALUE", cleaned, text)
            self.assertNotIn("SECRETVALUE", cleaned, text)
            self.assertNotIn("0123456789abcdef", cleaned, text)
            self.assertIn("REDACTED", cleaned)
