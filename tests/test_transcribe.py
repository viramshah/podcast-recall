"""U3: publisher parsing, quality checks, safe downloads, the queue and the transcript flows.

Nothing here uses the network, a real model or ffprobe: downloads, Whisper and the audio probe
are replaced by fakes.
"""

from __future__ import annotations

import json
import os
import urllib.error
from pathlib import Path

from podcast_recall import core, jobs, net, paths, publisher, quality, transcribe_flow, transcripts
from podcast_recall.audio import AudioError, AudioInfo, InsufficientDiskSpace
from podcast_recall.cli import main as cli_main
from podcast_recall.models import Segment
from podcast_recall.net import DownloadError, FetchInfo
from tests.base import T0, Base

DURATION = 600


def make_vtt(count: int = 60, step: int = 10, words: int = 20, header: str = "WEBVTT") -> str:
    lines = [header, ""]
    for i in range(count):
        start, end = i * step, (i + 1) * step - 0.5
        lines.append(f"{start // 60:02d}:{start % 60:02d}.000 --> {int(end) // 60:02d}:{int(end) % 60:02d}.500")
        lines.append(" ".join(f"w{i}x{j}" for j in range(words)))
        lines.append("")
    return "\n".join(lines)


def whisper_raw(count: int = 60, step: int = 10, words: int = 20, language: str = "en") -> dict:
    segments = []
    for i in range(count):
        text = " ".join(f"w{i}x{j}" for j in range(words))
        timed = [
            {"word": f" w{i}x{j}", "start": i * step + j * 0.4, "end": i * step + j * 0.4 + 0.3}
            for j in range(words)
        ]
        segments.append({"start": i * step, "end": (i + 1) * step - 0.5, "text": " " + text, "words": timed})
    return {"language": language, "segments": segments}


class FakeFetcher:
    """Same `fetch_to_file` as SafeFetcher, serving bytes from a dictionary."""

    def __init__(self, files: dict[str, bytes | Exception]) -> None:
        self.files = files
        self.urls: list[str] = []

    def fetch_to_file(self, url, dest, *, max_bytes, total_timeout_s, accept=None):
        self.urls.append(url)
        data = self.files.get(url)
        if data is None:
            raise DownloadError("example.com answered HTTP 404")
        if isinstance(data, Exception):
            raise data
        content_type = "audio/mpeg" if url.endswith(".mp3") else "text/vtt"
        if accept is not None and not accept(content_type):
            raise DownloadError(f"unexpected content type {content_type}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return FetchInfo(content_type, len(data), "example.com")


class TranscribeBase(Base):
    def setUp(self):
        super().setUp()
        self.conn.execute(
            "INSERT INTO feeds (feed_id, title, url, language) VALUES (1, 'Show', 'https://f/x', 'en-US')"
        )
        self.conn.commit()
        self.whisper_calls: list[tuple] = []
        self.audio_seconds = float(DURATION)
        self.raw = whisper_raw()

    def add_episode(self, episode_id: int, *, vtt: bool = True, duration: int = DURATION, matched: bool = True):
        transcripts_list = (
            [{"url": f"https://t.example.com/{episode_id}.vtt", "type": "text/vtt"}] if vtt else []
        )
        self.conn.execute(
            "INSERT INTO episodes (episode_id, feed_id, title, duration_s, audio_url, audio_type, "
            "transcript_url, transcripts_json, fetched_at) VALUES (?, 1, ?, ?, ?, 'audio/mpeg', ?, ?, ?)",
            (
                episode_id, f"Episode {episode_id}", duration,
                f"https://a.example.com/{episode_id}.mp3",
                transcripts_list[0]["url"] if transcripts_list else None,
                json.dumps(transcripts_list), T0,
            ),
        )
        video_id = f"vid{episode_id:08d}"
        self.conn.commit()
        return video_id

    def match_episode(self, episode_id: int, status: str = "matched") -> None:
        # episode_matches.video_id references videos; foreign keys are checked at commit time
        # only if enforced, so create a minimal video row through the real store helper.
        from podcast_recall import store
        from tests.fake_pi import make_video

        video_id = f"vid{episode_id:08d}"
        store.save_videos(
            self.conn, [video_id],
            [make_video(video_id, f"Episode {episode_id}", "2026-11-01T00:00:00", DURATION)], T0,
        )
        self.conn.execute(
            "INSERT INTO episode_matches (video_id, episode_id, status, resolved_at) VALUES (?, ?, ?, ?)",
            (video_id, episode_id, status, T0),
        )
        self.conn.commit()

    def services(self, files: dict | None = None, **kwargs) -> transcribe_flow.Services:
        files = files if files is not None else {}

        def transcriber(path, model, language):
            self.whisper_calls.append((path, model, language))
            return self.raw

        defaults = {
            "fetcher": FakeFetcher(files),
            "transcriber": transcriber,
            "prober": lambda path: AudioInfo(self.audio_seconds),
            "free_bytes": lambda path: 10**12,
            "clock": lambda: 0.0,
        }
        defaults.update(kwargs)
        return transcribe_flow.Services(**defaults)

    def work(self, services=None, **kwargs):
        return transcribe_flow.run_queue(
            self.conn, services or self.services(), now=lambda: self.clock, **kwargs
        )

    def job(self, episode_id: int):
        return self.conn.execute("SELECT * FROM jobs WHERE episode_id = ?", (episode_id,)).fetchone()

    def row(self, episode_id: int):
        return transcripts.get_row(self.conn, episode_id)

    def episode_with_publisher(self, episode_id: int = 1):
        self.add_episode(episode_id)
        self.match_episode(episode_id)
        return {f"https://t.example.com/{episode_id}.vtt": make_vtt().encode()}

    def episode_with_audio_only(self, episode_id: int = 1):
        self.add_episode(episode_id, vtt=False)
        self.match_episode(episode_id)
        return {f"https://a.example.com/{episode_id}.mp3": b"fake audio bytes"}


# ---------------------------------------------------------------------------- publisher parsing

VTT_REAL = """WEBVTT

NOTE this is a comment

intro
00:00:01.000 --> 00:00:04.000
<v SPEAKER_00>Welcome &amp; hello</v>

00:00:04.000 --> 00:00:06.500
<v SPEAKER_01><i>Thanks</i> for having me</v>

01:00.000 --> 01:03.000
a line with minutes only
"""

SRT_REAL = """1
00:00:01,000 --> 00:00:03,500
First line

2
00:00:03,500 --> 00:00:05,000
Second line
<b>bold</b>
"""


class PublisherParsing(TranscribeBase):
    def test_vtt_keeps_speaker_decodes_entities_and_ignores_notes(self):
        segments = publisher.parse_cues(VTT_REAL, "vtt")
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[0].text, "Welcome & hello")
        self.assertEqual(segments[0].speaker, "SPEAKER_00")
        self.assertEqual(segments[1].text, "Thanks for having me")
        self.assertEqual(segments[2].start, 60.0)

    def test_srt_with_comma_times(self):
        segments = publisher.parse_cues(SRT_REAL, "srt")
        self.assertEqual([s.start for s in segments], [1.0, 3.5])
        self.assertEqual(segments[1].text, "Second line bold")

    def test_consecutive_identical_cues_are_merged(self):
        text = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n\n00:00:02.000 --> 00:00:03.000\nhello\n"
        segments = publisher.parse_cues(text, "vtt")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].end, 3.0)

    def test_broken_files_are_rejected(self):
        with self.assertRaises(publisher.TranscriptParseError):
            publisher.parse_cues("not a transcript", "vtt")
        with self.assertRaises(publisher.TranscriptParseError):
            publisher.parse_cues("WEBVTT\n\n00:00:05.000 --> 00:00:02.000\nbackwards\n", "vtt")
        with self.assertRaises(publisher.TranscriptParseError):
            publisher.parse_cues("WEBVTT\n\n", "vtt")

    def test_vtt_is_preferred_over_srt_and_html_is_ignored(self):
        options = [
            {"url": "https://x/a.html", "type": "text/html"},
            {"url": "https://x/a.srt", "type": "application/x-subrip"},
            {"url": "https://x/a.vtt", "type": "text/vtt"},
        ]
        self.assertEqual(publisher.pick_transcript(options, None), ("https://x/a.vtt", "vtt"))
        self.assertIsNone(publisher.pick_transcript([{"url": "https://x/a.html", "type": "text/html"}], None))
        self.assertEqual(publisher.pick_transcript([], "https://x/b.srt"), ("https://x/b.srt", "srt"))


# ---------------------------------------------------------------------------- quality rules


def seg(start: float, end: float, text: str) -> Segment:
    return Segment(start, end, text)


class QualityRules(TranscribeBase):
    def test_a_good_publisher_transcript_passes(self):
        segments = publisher.parse_cues(make_vtt(), "vtt")
        self.assertEqual(quality.check_publisher(segments, DURATION), [])

    def test_publisher_transcript_that_is_too_short_or_ends_early_fails(self):
        tiny = [seg(0, 5, "just a few words")]
        self.assertTrue(quality.check_publisher(tiny, DURATION))
        half = publisher.parse_cues(make_vtt(count=30), "vtt")
        reasons = quality.check_publisher(half, DURATION)
        self.assertTrue(any("ends at" in r for r in reasons))

    def test_publisher_check_without_feed_duration_skips_the_end_test(self):
        half = publisher.parse_cues(make_vtt(count=30), "vtt")
        self.assertEqual(quality.check_publisher(half, None), [])

    def test_whisper_flags(self):
        good = [seg(i * 10, i * 10 + 9.5, " ".join("w" * 1 for _ in range(20))) for i in range(60)]
        review = quality.check_whisper(
            good, audio_duration_s=600, language="en", feed_language="en-US", feed_duration_s=600
        )
        self.assertEqual(review.flags, [])
        mismatch = quality.check_whisper(
            good, audio_duration_s=600, language="hi", feed_language="en", feed_duration_s=600
        )
        self.assertIn("language_mismatch", mismatch.blocking)
        early = quality.check_whisper(
            good[:30], audio_duration_s=600, language="en", feed_language="en", feed_duration_s=600
        )
        self.assertIn("ends_early", early.blocking)
        gap = quality.check_whisper(
            [seg(0, 5, "a " * 400), seg(500, 600, "b " * 400)],
            audio_duration_s=600, language="en", feed_language="en", feed_duration_s=600,
        )
        self.assertIn("long_gap", gap.blocking)
        empty = quality.check_whisper([], audio_duration_s=600, language="en", feed_language="en",
                                      feed_duration_s=600)
        self.assertEqual(empty.blocking, ["empty"])

    def test_info_flags_do_not_block(self):
        long = [seg(0, 4 * 3600, "word " * 4 * 3600 * 2)]
        review = quality.check_whisper(
            long, audio_duration_s=4 * 3600, language="en", feed_language="en", feed_duration_s=3600
        )
        self.assertEqual(review.blocking, [])
        self.assertIn("very_long_episode", review.info)
        self.assertIn("audio_duration_mismatch", review.info)


# ---------------------------------------------------------------------------- safe downloads


class SafeDownloads(Base):
    def test_only_public_addresses_are_allowed(self):
        for bad in ("127.0.0.1", "::1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "100.64.0.1",
                    "0.0.0.0", "::ffff:127.0.0.1", "not-an-ip"):
            self.assertFalse(net.is_public(bad), bad)
        for good in ("8.8.8.8", "2606:4700:4700::1111"):
            self.assertTrue(net.is_public(good), good)

    def test_urls_are_checked(self):
        public = lambda host, port: ["93.184.216.34"]
        self.assertEqual(net.check_url("https://example.com/a.mp3", public), "example.com")
        for url in ("file:///etc/passwd", "ftp://example.com/a", "https://user:pw@example.com/a",
                    "http:///nohost"):
            with self.assertRaises(DownloadError, msg=url):
                net.check_url(url, public)
        with self.assertRaises(DownloadError):
            net.check_url("http://localhost:11434/api", lambda host, port: ["127.0.0.1"])
        with self.assertRaises(DownloadError):
            net.check_url("http://mixed.example.com/", lambda host, port: ["93.184.216.34", "10.0.0.1"])

    def test_a_redirect_to_a_private_address_is_refused(self):
        handler = net._GuardedRedirect(lambda host, port: ["127.0.0.1"] if host == "evil.test" else ["8.8.8.8"])
        import urllib.request

        request = urllib.request.Request("https://good.example.com/a")
        with self.assertRaises(DownloadError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://evil.test/inner")

    def test_fetch_writes_atomically_and_enforces_size(self):
        class Response:
            def __init__(self, data: bytes, headers: dict):
                self.data, self.headers, self.pos = data, headers, 0

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n):
                chunk = self.data[self.pos:self.pos + n]
                self.pos += n
                return chunk

        body = b"x" * 1000
        fetcher = net.SafeFetcher(
            resolver=lambda host, port: ["8.8.8.8"],
            open_url=lambda url, timeout: Response(body, {"Content-Type": "audio/mpeg"}),
        )
        dest = Path(self.home) / "out" / "a.bin"
        info = fetcher.fetch_to_file("https://example.com/a", dest, max_bytes=5000, total_timeout_s=60)
        self.assertEqual(info.size, 1000)
        self.assertEqual(dest.read_bytes(), body)
        self.assertFalse(dest.with_name("a.bin.part").exists())
        small = Path(self.home) / "out" / "b.bin"
        with self.assertRaises(DownloadError):
            fetcher.fetch_to_file("https://example.com/a", small, max_bytes=500, total_timeout_s=60)
        self.assertFalse(small.exists())
        self.assertFalse(small.with_name("b.bin.part").exists())

    def test_wrong_content_type_and_http_errors(self):
        class Html:
            def __init__(self):
                self.headers = {"Content-Type": "text/html"}

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, n):
                return b""

        fetcher = net.SafeFetcher(resolver=lambda h, p: ["8.8.8.8"], open_url=lambda u, t: Html())
        with self.assertRaises(DownloadError):
            fetcher.fetch_to_file("https://example.com/a", Path(self.home) / "c", max_bytes=10,
                                  total_timeout_s=5, accept=lambda ct: ct.startswith("audio/"))

        def boom(url, timeout):
            raise urllib.error.HTTPError(url, 503, "no", {}, None)

        failing = net.SafeFetcher(resolver=lambda h, p: ["8.8.8.8"], open_url=boom)
        with self.assertRaises(DownloadError) as caught:
            failing.fetch_to_file("https://example.com/secret?token=abc", Path(self.home) / "d",
                                  max_bytes=10, total_timeout_s=5)
        self.assertNotIn("token", str(caught.exception))


# ---------------------------------------------------------------------------- the queue


class QueueRules(TranscribeBase):
    def test_only_matched_episodes_are_enqueued(self):
        for episode_id, status in ((1, "matched"), (2, "needs_review"), (3, "unmatched")):
            self.add_episode(episode_id)
            self.match_episode(episode_id, status)
        self.assertEqual(jobs.enqueue_matched(self.conn, T0), 1)
        self.assertEqual(jobs.enqueue_matched(self.conn, T0), 0)  # not twice
        self.assertIsNotNone(self.job(1))
        self.assertIsNone(self.job(2))

    def test_publisher_jobs_run_first_then_whisper_shortest_first(self):
        self.add_episode(1, vtt=False, duration=3000)
        self.add_episode(2, vtt=False, duration=1000)
        self.add_episode(3, vtt=True, duration=5000)
        for episode_id in (1, 2, 3):
            self.match_episode(episode_id)
        jobs.enqueue_matched(self.conn, T0)
        order = [r["episode_id"] for r in jobs.due_jobs(self.conn, T0)]
        self.assertEqual(order, [3, 2, 1])

    def test_failures_back_off_then_fail_after_three_attempts(self):
        self.add_episode(1)
        self.match_episode(1)
        jobs.enqueue_matched(self.conn, T0)
        self.assertEqual(jobs.record_failure(self.conn, 1, "boom", T0), "queued")
        self.assertEqual(self.job(1)["not_before"], "2026-11-17T12:02:00Z")
        self.assertEqual(jobs.due_jobs(self.conn, T0), [])
        self.assertEqual(jobs.record_failure(self.conn, 1, "boom", "2026-11-17T12:03:00Z"), "queued")
        self.assertEqual(self.job(1)["not_before"], "2026-11-17T12:13:00Z")
        self.assertEqual(jobs.record_failure(self.conn, 1, "boom", "2026-11-17T12:14:00Z"), "failed")
        self.assertEqual(self.job(1)["attempts"], 3)

    def test_crash_recovery_does_not_use_an_attempt(self):
        self.add_episode(1)
        self.match_episode(1)
        jobs.enqueue_matched(self.conn, T0)
        jobs.set_state(self.conn, 1, "transcribing", T0)
        self.assertEqual(jobs.recover(self.conn, T0), 1)
        self.assertEqual(self.job(1)["state"], "queued")
        self.assertEqual(self.job(1)["attempts"], 0)

    def test_only_one_worker_at_a_time(self):
        from podcast_recall.errors import SyncAlreadyRunning
        from podcast_recall.lock import SyncLock

        with SyncLock(paths.transcribe_lock_path()), self.assertRaises(SyncAlreadyRunning):
            core.run_transcribe(conn=self.conn, now=self.now, services=self.services())


# ---------------------------------------------------------------------------- the flows


class PublisherFlow(TranscribeBase):
    def test_publisher_success_downloads_no_audio(self):
        files = self.episode_with_publisher()
        services = self.services(files)
        result = self.work(services)
        self.assertEqual([o.source for o in result.outcomes], ["publisher"])
        self.assertEqual(services.fetcher.urls, ["https://t.example.com/1.vtt"])
        self.assertEqual(self.whisper_calls, [])
        row = self.row(1)
        self.assertEqual((row["source"], row["timing_detail"], row["status"]), ("publisher", "chunk", "ok"))
        self.assertEqual(self.job(1)["state"], "done")
        loaded = transcripts.load_transcript(self.conn, 1)
        self.assertEqual(len(loaded.segments), 60)
        self.assertTrue((paths.raw_transcripts_dir() / "1.vtt").exists())

    def test_transcript_file_matches_the_contract_and_is_not_half_written(self):
        files = self.episode_with_publisher()
        self.work(self.services(files))
        path = paths.transcripts_dir() / "1.json"
        data = json.loads(path.read_text())
        self.assertEqual(
            set(data),
            {"episode_id", "source", "timing_detail", "model", "language", "audio_duration_s",
             "created_at", "segments"},
        )
        self.assertEqual(data["source"], "publisher")
        self.assertEqual(set(data["segments"][0]) - {"speaker"}, {"start", "end", "text", "words"})
        self.assertEqual([p.name for p in path.parent.glob("*.tmp")], [])

    def test_a_rejected_publisher_transcript_falls_back_to_whisper_with_a_reason(self):
        files = self.episode_with_publisher()
        files["https://t.example.com/1.vtt"] = make_vtt(count=10).encode()  # ends at 17%
        files["https://a.example.com/1.mp3"] = b"audio"
        result = self.work(self.services(files))
        outcome = result.outcomes[0]
        self.assertEqual(outcome.source, "whisper")
        self.assertIn("ends at", outcome.fallback_reason)
        self.assertIn("ends at", self.row(1)["fallback_reason"])
        self.assertFalse((paths.raw_transcripts_dir() / "1.vtt").exists())

    def test_a_missing_or_unparseable_publisher_file_falls_back(self):
        files = self.episode_with_publisher()
        files["https://t.example.com/1.vtt"] = b"garbage"
        files["https://a.example.com/1.mp3"] = b"audio"
        outcome = self.work(self.services(files)).outcomes[0]
        self.assertEqual(outcome.source, "whisper")
        self.assertIn("unusable", outcome.fallback_reason)


class WhisperFlow(TranscribeBase):
    def test_whisper_success_deletes_audio_and_records_the_model(self):
        files = self.episode_with_audio_only()
        outcome = self.work(self.services(files)).outcomes[0]
        self.assertEqual((outcome.source, outcome.status), ("whisper", "ok"))
        self.assertEqual(outcome.fallback_reason, "no supported publisher transcript")
        self.assertEqual(list(paths.audio_dir().glob("*")), [])
        row = self.row(1)
        self.assertEqual((row["source"], row["timing_detail"]), ("whisper", "word"))
        self.assertEqual(row["model"], paths.DEFAULT_WHISPER_MODEL)
        self.assertEqual(self.whisper_calls[0][2], None)  # language is detected, never forced
        loaded = transcripts.load_transcript(self.conn, 1)
        self.assertTrue(loaded.segments[0].words)

    def test_keep_audio_keeps_the_file(self):
        files = self.episode_with_audio_only()
        self.work(self.services(files), keep_audio=True)
        self.assertEqual(len(list(paths.audio_dir().glob("1.*"))), 1)

    def test_language_override_is_passed_to_whisper(self):
        files = self.episode_with_audio_only()
        os.environ["PODCAST_RECALL_WHISPER_LANGUAGE"] = "hi"
        self.addCleanup(os.environ.pop, "PODCAST_RECALL_WHISPER_LANGUAGE", None)
        self.work(self.services(files))
        self.assertEqual(self.whisper_calls[0][2], "hi")

    def test_wrong_language_needs_review_and_accept_clears_it(self):
        files = self.episode_with_audio_only()
        self.raw = whisper_raw(language="hi")
        outcome = self.work(self.services(files)).outcomes[0]
        self.assertEqual(outcome.status, "needs_review")
        self.assertIn("language_mismatch", outcome.flags)
        status = core.transcribe_status(conn=self.conn, now=self.now)
        self.assertEqual(len(status.needs_review), 1)
        core.accept_transcript(1, conn=self.conn)
        self.assertEqual(self.row(1)["status"], "ok")

    def test_audio_that_is_not_audio_fails_the_job_and_removes_the_file(self):
        files = self.episode_with_audio_only()

        def bad_probe(path):
            raise AudioError("the file has no audio stream")

        result = self.work(self.services(files, prober=bad_probe))
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(self.job(1)["state"], "queued")
        self.assertEqual(self.job(1)["attempts"], 1)
        self.assertEqual(list(paths.audio_dir().glob("*")), [])

    def test_a_failed_download_is_recorded_and_the_run_continues(self):
        files = self.episode_with_audio_only(1)
        files.update(self.episode_with_audio_only(2))
        files["https://a.example.com/1.mp3"] = DownloadError("example.com answered HTTP 503")
        result = self.work(self.services(files))
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.outcomes), 1)
        self.assertIn("503", self.job(1)["last_error"])

    def test_no_disk_space_stops_the_run_without_using_an_attempt(self):
        files = self.episode_with_audio_only()
        with self.assertRaises(InsufficientDiskSpace):
            self.work(self.services(files, free_bytes=lambda p: 1000))
        self.assertEqual(self.job(1)["state"], "queued")
        self.assertEqual(self.job(1)["attempts"], 0)

    def test_ctrl_c_puts_the_job_back_without_using_an_attempt(self):
        files = self.episode_with_audio_only()

        def interrupted(path, model, language):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            self.work(self.services(files, transcriber=interrupted))
        self.assertEqual(self.job(1)["state"], "queued")
        self.assertEqual(self.job(1)["attempts"], 0)
        self.assertEqual(list(paths.audio_dir().glob("*")), [])

    def test_whisper_crash_is_an_ordinary_failure(self):
        files = self.episode_with_audio_only()

        def crash(path, model, language):
            raise RuntimeError("out of memory")

        result = self.work(self.services(files, transcriber=crash))
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(self.job(1)["attempts"], 1)

    def test_retry_with_whisper_skips_the_publisher_transcript(self):
        files = self.episode_with_publisher()
        files["https://a.example.com/1.mp3"] = b"audio"
        self.work(self.services(files))
        self.assertEqual(self.row(1)["source"], "publisher")
        core.retry_transcript(1, force_whisper=True, conn=self.conn, now=self.now)
        outcome = self.work(self.services(files)).outcomes[0]
        self.assertEqual(outcome.source, "whisper")
        self.assertEqual(outcome.fallback_reason, "forced to Whisper")
        self.assertEqual(self.row(1)["source"], "whisper")

    def test_retry_resets_attempts(self):
        self.add_episode(1)
        self.match_episode(1)
        jobs.enqueue_matched(self.conn, T0)
        for _ in range(3):
            jobs.record_failure(self.conn, 1, "x", T0)
        self.assertEqual(self.job(1)["state"], "failed")
        core.retry_transcript(1, conn=self.conn, now=self.now)
        self.assertEqual((self.job(1)["state"], self.job(1)["attempts"]), ("queued", 0))


class StatusAndShow(TranscribeBase):
    def test_status_counts_and_missing_files(self):
        files = self.episode_with_publisher(1)
        files.update(self.episode_with_audio_only(2))
        files["https://a.example.com/2.mp3"] = b"audio"
        self.work(self.services(files), limit=1)
        status = core.transcribe_status(conn=self.conn, now=self.now)
        self.assertEqual((status.matched_episodes, status.transcripts_ok, status.queued), (2, 1, 1))
        (paths.transcripts_dir() / "1.json").unlink()
        self.assertEqual(core.transcribe_status(conn=self.conn, now=self.now).missing_files, [1])

    def test_show_returns_the_window_around_a_time(self):
        files = self.episode_with_publisher()
        self.work(self.services(files))
        shown = core.show_transcript(1, 125.0, 10.0, conn=self.conn)
        starts = [s for s, _e, _t in shown.text_before_and_after]
        self.assertEqual(starts, [110, 120, 130])
        self.assertEqual(shown.total_segments, 60)

    def test_get_transcript_returns_none_without_a_transcript(self):
        self.assertIsNone(core.get_transcript(99, conn=self.conn))


class SeedScope(TranscribeBase):
    def test_a_run_limited_to_some_videos_ignores_other_episodes(self):
        files = self.episode_with_publisher(1)
        files.update(self.episode_with_publisher(2))
        result = core.run_transcribe(
            ["vid00000001"], conn=self.conn, now=self.now, services=self.services(files)
        )
        self.assertEqual(len(result.outcomes), 1)
        self.assertIsNone(self.row(2))
        self.assertIsNone(self.job(2))


# ---------------------------------------------------------------------------- the command line


class CliCommands(TranscribeBase):
    def setUp(self):
        super().setUp()
        self.home_db = Path(self.home)

    def test_help_and_show_for_a_missing_transcript_exit_with_an_error(self):
        from podcast_recall import store

        os.makedirs(self.home, exist_ok=True)
        os.chmod(self.home, 0o700)
        store.connect(paths.db_path(), paths.backup_dir()).close()
        code = cli_main(["transcribe", "show", "999"])
        self.assertEqual(code, 1)
        self.assertEqual(cli_main(["transcribe", "status"]), 0)

    def test_parse_at(self):
        from podcast_recall.cli import _mmss, _parse_at

        self.assertEqual(_parse_at("90"), 90.0)
        self.assertEqual(_parse_at("1:30"), 90.0)
        self.assertEqual(_parse_at("1:01:30"), 3690.0)
        self.assertEqual(_mmss(3690), "1:01:30")


class LanguageTags(TranscribeBase):
    def test_feed_language_is_primary_subtag(self):
        self.assertEqual(quality.primary_language("en-US"), "en")
        self.assertEqual(quality.primary_language("pt_BR"), "pt")
        self.assertEqual(quality.primary_language(None), "")
