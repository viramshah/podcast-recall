"""U4: chunking, the index, and search.

Nothing here needs Ollama or the network: a small fake embedder stands in. It maps words to
directions, with a few synonyms ("auto" and "car" share one), so meaning search can be shown to
find things keyword search cannot.
"""

from __future__ import annotations

import itertools
import math
import urllib.error
import zlib

from podcast_recall import chunker, core, embeddings, indexer, paths, retrieval, store, transcripts
from podcast_recall.cli import main as cli_main
from podcast_recall.errors import ApiError, ConfigError, SyncAlreadyRunning
from podcast_recall.models import Segment, Transcript
from tests.base import T0, Base
from tests.fake_pi import epoch, make_video

DIMS = 16
SYNONYMS = {"auto": "car", "automobile": "car", "vehicle": "car"}


def _bucket(word: str) -> int:
    return zlib.crc32(SYNONYMS.get(word, word).encode()) % DIMS


def fake_vector(text: str) -> list[float]:
    vec = [0.0] * DIMS
    for word in retrieval._WORD.findall(text.lower()):
        if word not in retrieval.STOPWORDS:
            vec[_bucket(word)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeEmbedder:
    def __init__(self, model: str = "fake-embed") -> None:
        self.model = model
        self.batches: list[int] = []
        self.fail_with: Exception | None = None
        self.fail_after: int | None = None  # number of successful calls before failing

    def embed_documents(self, texts):
        if self.fail_after is not None:
            if self.fail_after <= 0:
                raise self.fail_with or ApiError("embedder down")
            self.fail_after -= 1
        if self.fail_with is not None and self.fail_after is None:
            raise self.fail_with
        self.batches.append(len(texts))
        return [fake_vector(t) for t in texts]

    def embed_query(self, text):
        if self.fail_with is not None:
            raise self.fail_with
        return fake_vector(text)


KUBE = [
    "Today we talk about the kubernetes deployment pipeline for our team.",
    "A good pipeline has staging, review and a rollback plan.",
    "Rollbacks save you when a deployment goes wrong at night.",
]
BREAD = [
    "My sourdough starter needs feeding every single morning.",
    "Flour and water and patience make the best bread.",
    "A hot oven and steam give the crust its crackle.",
]
RUN = [
    "Marathon training starts with an easy long run on Sunday.",
    "Build the weekly mileage slowly and respect rest days.",
    "My car broke down on the way to the race, an awful morning.",
]


def filler(n: int, offset: int = 0) -> list[str]:
    return [f"Filler sentence number {offset + i} about the weather and nothing else." for i in range(n)]


class World:
    """Builds shows, episodes, library items, matches and saved transcripts in a database."""

    def __init__(self, conn) -> None:
        self.conn = conn
        for feed_id, title in ((1, "Lenny's Podcast"), (2, "Greg Show"), (3, "Lenny's Daily")):
            conn.execute("INSERT INTO feeds (feed_id, title, url, language) VALUES (?, ?, 'u', 'en')",
                         (feed_id, title))
        conn.commit()

    def add_episode(self, episode_id, feed_id, title, iso, sentences, *, users=("owner",),
                    status="ok", match="matched", segment_s=5.0, speaker=None):
        video_id = f"vid{episode_id:08d}"
        store.save_videos(self.conn, [video_id],
                          [make_video(video_id, title, iso, 600)], T0)
        self.conn.execute(
            "INSERT INTO episodes (episode_id, feed_id, title, published, duration_s, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (episode_id, feed_id, title, epoch(iso), int(len(sentences) * segment_s), T0),
        )
        self.conn.execute(
            "INSERT INTO episode_matches (video_id, episode_id, status, resolved_at) VALUES (?, ?, ?, ?)",
            (video_id, episode_id, match, T0),
        )
        for user in users:
            self.conn.execute(
                "INSERT INTO library_items (user_id, video_id, source, first_seen_at) VALUES (?, ?, 'liked', ?)",
                (user, video_id, T0),
            )
        self.conn.commit()
        if status:
            self.save_transcript(episode_id, sentences, status=status, segment_s=segment_s, speaker=speaker)
        return video_id

    def save_transcript(self, episode_id, sentences, *, status="ok", segment_s=5.0, speaker=None):
        segments = [
            Segment(i * segment_s, i * segment_s + segment_s - 0.2, text, speaker, [])
            for i, text in enumerate(sentences)
        ]
        transcripts.save_transcript(
            self.conn,
            Transcript(episode_id=episode_id, source="publisher", timing_detail="chunk",
                       model="publisher:vtt", language="en", audio_duration_s=600, created_at=T0,
                       segments=segments, status=status, flags=[], publisher_url=None,
                       fallback_reason=None),
        )


class IndexBase(Base):
    def setUp(self):
        super().setUp()
        store.upsert_user(self.conn, "other", "UCo", "Other", T0)
        self.world = World(self.conn)
        self.embedder = FakeEmbedder()
        self.services = indexer.IndexServices(embedder=self.embedder)

    def build(self, **kwargs):
        return indexer.build_index(self.conn, kwargs.pop("services", self.services),
                                   now=self.now, **kwargs)

    def find(self, query, user="owner", **kwargs):
        return retrieval.find(self.conn, self.embedder, query, user, **kwargs)

    @staticmethod
    def ids(result) -> set[int]:
        return {h.episode_id for h in result.hits}

    def chunk_count(self, episode_id=None):
        sql, args = "SELECT COUNT(*) FROM chunks", ()
        if episode_id is not None:
            sql, args = sql + " WHERE episode_id = ?", (episode_id,)
        return self.conn.execute(sql, args).fetchone()[0]

    def vector_count(self):
        from podcast_recall import vectors

        vectors.load(self.conn)
        return vectors.row_count(self.conn)

    def three_episodes(self):
        self.world.add_episode(101, 1, "Shipping with Kubernetes", "2026-10-01T10:00:00", KUBE)
        self.world.add_episode(102, 2, "Bread Basics", "2026-10-15T10:00:00", BREAD)
        self.world.add_episode(103, 1, "Running a Marathon", "2026-11-01T10:00:00", RUN)


# ---------------------------------------------------------------------------- chunking


def seg(start: float, end: float, text: str, speaker: str | None = None) -> Segment:
    return Segment(start, end, text, speaker, [])


class Chunking(Base):
    def segments(self, count=60, step=5.0):
        return [seg(i * step, i * step + step - 0.2, f"segment {i} has some words") for i in range(count)]

    def test_chunks_are_about_75_seconds_overlap_by_about_15_and_cover_everything(self):
        chunks = chunker.chunk_segments(self.segments())
        self.assertEqual([c.chunk_no for c in chunks], list(range(len(chunks))))
        for c in chunks[:-1]:
            self.assertLessEqual(c.end_s - c.start_s, chunker.TARGET_S)
            self.assertGreater(c.end_s - c.start_s, chunker.TARGET_S - 10)
        for a, b in itertools.pairwise(chunks):
            overlap = a.end_s - b.start_s
            self.assertGreaterEqual(overlap, chunker.OVERLAP_S - 5)
            self.assertLessEqual(overlap, chunker.OVERLAP_S + 5)
        self.assertEqual(chunks[0].start_s, 0.0)
        self.assertEqual(chunks[-1].end_s, 299.8)
        joined = " ".join(c.text for c in chunks)
        for i in range(60):
            self.assertIn(f"segment {i} ", joined + " ")

    def test_it_is_deterministic(self):
        self.assertEqual(chunker.chunk_segments(self.segments()), chunker.chunk_segments(self.segments()))

    def test_a_segment_is_never_cut(self):
        long = [seg(0, 100, "one very long segment spoken without a break"), seg(100, 104, "short")]
        chunks = chunker.chunk_segments(long)
        self.assertEqual(chunks[0].text, "one very long segment spoken without a break")
        self.assertEqual((chunks[0].start_s, chunks[0].end_s), (0, 100))
        self.assertIn("short", chunks[-1].text)

    def test_empty_and_blank_input(self):
        self.assertEqual(chunker.chunk_segments([]), [])
        self.assertEqual(chunker.chunk_segments([seg(0, 1, "   ")]), [])

    def test_out_of_order_and_overlapping_segments_are_sorted_and_kept(self):
        messy = [seg(5, 9, "second"), seg(0, 5.5, "first"), seg(4.9, 8, "overlapping")]
        chunks = chunker.chunk_segments(messy)
        self.assertEqual(chunks[0].text, "first overlapping second")

    def test_speaker_only_when_one_label_covers_more_than_half_the_words(self):
        mostly_a = [seg(0, 5, "a a a a a a", "SPEAKER_00"), seg(5, 10, "b b", "SPEAKER_01")]
        self.assertEqual(chunker.chunk_segments(mostly_a)[0].speaker, "SPEAKER_00")
        even = [seg(0, 5, "a a a", "SPEAKER_00"), seg(5, 10, "b b b", "SPEAKER_01")]
        self.assertIsNone(chunker.chunk_segments(even)[0].speaker)
        none = [seg(0, 5, "a a a")]
        self.assertIsNone(chunker.chunk_segments(none)[0].speaker)

    def test_speaker_labels_are_not_part_of_the_text(self):
        chunks = chunker.chunk_segments([seg(0, 5, "hello there", "SPEAKER_00")])
        self.assertNotIn("SPEAKER", chunks[0].text)

    def test_word_count(self):
        self.assertEqual(chunker.chunk_segments([seg(0, 5, "one two three")])[0].word_count, 3)


# ---------------------------------------------------------------------------- query parsing


class QueryParsing(Base):
    def test_plain_words_phrases_and_stop_words(self):
        phrases, words = retrieval.parse_query('How do I ship "agent harness" fast')
        self.assertEqual(phrases, [["agent", "harness"]])
        self.assertEqual(words, ["do", "ship", "fast"])

    def test_operators_and_symbols_are_only_words(self):
        phrases, words = retrieval.parse_query('AI agents AND (harness*) OR NEAR "unbalanced')
        self.assertEqual(phrases, [])
        # "and" and "or" are stop words and dropped; "near" stays but is quoted, so it is not an operator
        self.assertEqual(words, ["ai", "agents", "harness", "near", "unbalanced"])
        expression = retrieval.fts_expression(phrases, words)
        self.assertEqual(expression, '"ai" OR "agents" OR "harness" OR "near" OR "unbalanced"')

    def test_only_stop_words_falls_back_to_all_words(self):
        self.assertEqual(retrieval.parse_query("what is the")[1], ["what", "is", "the"])

    def test_nothing_to_search_for(self):
        self.assertIsNone(retrieval.fts_expression(*retrieval.parse_query('"" ?? !!')))

    def test_apostrophes_are_kept_inside_words(self):
        self.assertEqual(retrieval.parse_query("don't stop")[1], ["don't", "stop"])

    def test_very_long_queries_are_cut(self):
        words = retrieval.parse_query("word " * 5000)[1]
        self.assertLessEqual(len(words), retrieval.MAX_QUERY_CHARS // 5)


# ---------------------------------------------------------------------------- the embeddings client


class EmbeddingsClient(Base):
    def client(self, post, model="nomic-embed-text"):
        self.sleeps = []
        return embeddings.OllamaEmbedder("http://127.0.0.1:11434", model, post=post, sleep=self.sleeps.append)

    def test_documents_and_queries_get_the_prefixes_and_are_sent_in_batches_of_16(self):
        sent = []

        def post(url, payload, timeout):
            sent.append((url, payload, timeout))
            return {"embeddings": [[0.1, 0.2]] * len(payload["input"])}

        client = self.client(post)
        vectors = client.embed_documents([f"text {i}" for i in range(20)])
        self.assertEqual(len(vectors), 20)
        self.assertEqual([len(p["input"]) for _u, p, _t in sent], [16, 4])
        self.assertTrue(all(i.startswith("search_document: ") for _u, p, _t in sent for i in p["input"]))
        self.assertEqual(sent[0][0], "http://127.0.0.1:11434/api/embed")
        self.assertEqual(sent[0][2], embeddings.TIMEOUT_S)
        client.embed_query("hello")
        self.assertEqual(sent[-1][1]["input"], ["search_query: hello"])

    def test_a_missing_model_says_how_to_install_it(self):
        def post(url, payload, timeout):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)

        with self.assertRaises(embeddings.EmbeddingUnavailable) as caught:
            self.client(post).embed_query("x")
        self.assertIn("ollama pull nomic-embed-text", str(caught.exception))

    def test_ollama_not_running_stops_at_once_with_a_clear_message(self):
        calls = []

        def post(url, payload, timeout):
            calls.append(1)
            raise urllib.error.URLError("connection refused")

        with self.assertRaises(embeddings.EmbeddingUnavailable) as caught:
            self.client(post).embed_documents(["x"])
        self.assertIn("Ollama", str(caught.exception))
        self.assertEqual(len(calls), 1)

    def test_a_temporary_failure_is_retried(self):
        state = {"n": 0}

        def post(url, payload, timeout):
            state["n"] += 1
            if state["n"] < 3:
                raise TimeoutError("slow")
            return {"embeddings": [[1.0]]}

        client = self.client(post)
        self.assertEqual(client.embed_query("x"), [1.0])
        self.assertEqual(state["n"], 3)
        self.assertEqual(len(self.sleeps), 2)

    def test_after_three_attempts_it_gives_up(self):
        def post(url, payload, timeout):
            raise TimeoutError("slow")

        with self.assertRaises(ApiError):
            self.client(post).embed_query("x")
        self.assertEqual(len(self.sleeps), embeddings.ATTEMPTS - 1)

    def test_a_wrong_number_of_vectors_is_an_error(self):
        def post(url, payload, timeout):
            return {"embeddings": []}

        with self.assertRaises(ApiError):
            self.client(post).embed_query("x")

    def test_only_loopback_addresses_are_allowed(self):
        for url in ("http://127.0.0.1:11434", "http://localhost:11434/", "http://[::1]:11434"):
            embeddings.check_loopback(url)
        for url in ("http://192.168.1.5:11434", "http://example.com", "file:///etc/passwd", "ftp://127.0.0.1"):
            with self.assertRaises(ConfigError, msg=url):
                embeddings.check_loopback(url)


# ---------------------------------------------------------------------------- the index


class Indexing(IndexBase):
    def test_only_ok_transcripts_are_indexed(self):
        self.three_episodes()
        self.world.add_episode(104, 1, "Flagged", "2026-11-02T10:00:00", KUBE, status="needs_review")
        self.world.add_episode(105, 1, "No transcript", "2026-11-03T10:00:00", KUBE, status=None)
        result = self.build()
        self.assertEqual(result.indexed, 3)
        self.assertEqual(self.chunk_count(104), 0)
        self.assertEqual(self.chunk_count(105), 0)
        self.assertEqual(self.vector_count(), self.chunk_count())

    def test_a_second_build_does_nothing(self):
        self.three_episodes()
        self.build()
        again = self.build()
        self.assertEqual((again.indexed, again.up_to_date), (0, 3))

    def test_accepting_a_flagged_transcript_makes_it_indexable_on_the_next_build(self):
        self.world.add_episode(104, 1, "Flagged", "2026-11-02T10:00:00", KUBE, status="needs_review")
        self.assertEqual(self.build().indexed, 0)
        transcripts.accept(self.conn, 104)
        self.assertEqual(self.build().indexed, 1)

    def test_a_changed_transcript_is_indexed_again_and_old_chunks_are_gone(self):
        self.three_episodes()
        self.build()
        self.world.save_transcript(101, ["Completely new words about astronomy and telescopes."])
        result = self.build()
        self.assertEqual((result.indexed, result.up_to_date), (1, 2))
        self.assertFalse(any("kubernetes" in h.text for h in self.find("kubernetes").hits))
        self.assertEqual(self.find("telescopes").hits[0].episode_id, 101)
        self.assertEqual(self.vector_count(), self.chunk_count())

    def test_a_new_chunking_version_redoes_every_episode(self):
        self.three_episodes()
        self.build()
        original = chunker.CHUNKING_VERSION
        self.addCleanup(setattr, chunker, "CHUNKING_VERSION", original)
        chunker.CHUNKING_VERSION = original + 1
        self.assertEqual(self.build().indexed, 3)

    def test_a_different_embedding_model_re_embeds(self):
        self.three_episodes()
        self.build()
        newer = indexer.IndexServices(embedder=FakeEmbedder("other-model"))
        self.assertEqual(self.build(services=newer).indexed, 3)
        models = {r[0] for r in self.conn.execute("SELECT embed_model FROM index_state")}
        self.assertEqual(models, {"other-model"})

    def test_rebuild_redoes_everything(self):
        self.three_episodes()
        self.build()
        self.assertEqual(self.build(rebuild=True).indexed, 3)
        self.assertEqual(self.vector_count(), self.chunk_count())

    def test_an_embedding_failure_leaves_the_old_chunks_in_place(self):
        self.three_episodes()
        self.build()
        before = self.conn.execute("SELECT chunk_id, text FROM chunks WHERE episode_id = 101 ORDER BY chunk_id").fetchall()
        self.world.save_transcript(101, ["Brand new content about gardening and tomatoes."])
        self.embedder.fail_with = ApiError("embedder down")
        with self.assertRaises(ApiError):
            self.build()
        after = self.conn.execute("SELECT chunk_id, text FROM chunks WHERE episode_id = 101 ORDER BY chunk_id").fetchall()
        self.assertEqual([tuple(r) for r in before], [tuple(r) for r in after])
        self.assertEqual(self.vector_count(), self.chunk_count())
        self.embedder.fail_with = None
        self.assertEqual(self.build().indexed, 1)
        self.assertEqual(self.find("tomatoes").hits[0].episode_id, 101)

    def test_a_crash_after_some_episodes_keeps_those_and_resumes(self):
        self.three_episodes()
        self.embedder.fail_after = 2  # the third episode fails
        self.embedder.fail_with = ApiError("embedder down")
        with self.assertRaises(ApiError):
            self.build()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM index_state").fetchone()[0], 2)
        self.embedder.fail_after = None
        self.embedder.fail_with = None
        result = self.build()
        self.assertEqual((result.indexed, result.up_to_date), (1, 2))
        self.assertEqual(self.vector_count(), self.chunk_count())

    def test_ollama_down_writes_nothing_for_a_new_episode(self):
        self.three_episodes()
        self.embedder.fail_with = embeddings.EmbeddingUnavailable("Ollama is not running")
        with self.assertRaises(embeddings.EmbeddingUnavailable):
            self.build()
        self.assertEqual(self.chunk_count(), 0)

    def test_a_transcript_that_stops_being_ok_is_removed_from_the_index(self):
        self.three_episodes()
        self.build()
        self.conn.execute("UPDATE transcripts SET status = 'needs_review' WHERE episode_id = 101")
        self.conn.commit()
        result = self.build()
        self.assertEqual(result.removed, 1)
        self.assertEqual(self.chunk_count(101), 0)
        self.assertEqual(self.vector_count(), self.chunk_count())
        self.assertNotIn(101, self.ids(self.find("kubernetes")))

    def test_without_vectors_keyword_search_works_and_a_later_build_adds_vectors(self):
        self.three_episodes()
        off = indexer.IndexServices(embedder=self.embedder, use_vectors=False)
        result = self.build(services=off)
        self.assertEqual(result.vectors_used, False)
        self.assertEqual(self.conn.execute("SELECT SUM(embedded) FROM index_state").fetchone()[0], 0)
        self.assertEqual(self.find("sourdough", use_vectors=False).hits[0].episode_id, 102)
        later = self.build()
        self.assertEqual(later.indexed, 3)
        self.assertEqual(self.vector_count(), self.chunk_count())

    def test_the_build_can_be_limited_to_some_episodes(self):
        self.three_episodes()
        self.assertEqual(self.build(only_episode_ids={101}).indexed, 1)
        self.assertEqual(self.chunk_count(102), 0)

    def test_progress_events_are_reported(self):
        self.three_episodes()
        events = []
        self.build(on_progress=events.append)
        self.assertEqual([e["stage"] for e in events], ["start", "done"] * 3)

    def test_status_counts(self):
        self.three_episodes()
        before = indexer.index_status(self.conn, "fake-embed")
        self.assertEqual((before.episodes_indexed, before.waiting), (0, 0 + 3))
        self.build()
        after = indexer.index_status(self.conn, "fake-embed")
        self.assertEqual((after.episodes_indexed, after.waiting, after.without_vectors), (3, 0, 0))
        self.assertEqual(after.vector_rows, after.chunks)

    def test_a_vector_size_change_recreates_the_vector_table(self):
        from podcast_recall import vectors

        self.three_episodes()
        self.build()
        vectors.load(self.conn)
        self.assertTrue(vectors.ensure_table(self.conn, DIMS + 4))
        self.assertEqual(vectors.row_count(self.conn), 0)
        self.assertEqual(self.conn.execute("SELECT SUM(embedded) FROM index_state").fetchone()[0], 0)

    def test_nothing_is_logged(self):
        self.three_episodes()
        with self.assertNoLogs():
            self.build()
            self.find("kubernetes pipeline")


# ---------------------------------------------------------------------------- search


class Searching(IndexBase):
    def setUp(self):
        super().setUp()
        self.three_episodes()
        self.build()

    def test_keyword_search_finds_the_right_episode_with_time_and_link(self):
        hit = self.find("sourdough starter").hits[0]
        self.assertEqual(hit.episode_id, 102)
        self.assertEqual(hit.show, "Greg Show")
        self.assertEqual(hit.title, "Bread Basics")
        self.assertEqual(hit.start_s, 0.0)
        self.assertEqual(hit.url, "https://youtu.be/vid00000102?t=0")
        self.assertIsNotNone(hit.keyword_rank)

    def test_meaning_search_finds_what_keywords_cannot(self):
        self.assertEqual(self.find("automobile", use_vectors=False).hits, [])
        result = self.find("automobile")
        self.assertTrue(result.vectors_used)
        self.assertEqual(result.hits[0].episode_id, 103)
        self.assertIsNone(result.hits[0].keyword_rank)
        self.assertEqual(result.hits[0].vector_rank, 1)
        self.assertLess(result.hits[0].vector_distance, result.hits[-1].vector_distance)

    def test_a_quoted_phrase_must_match_exactly(self):
        self.world.add_episode(106, 1, "Animals", "2026-11-05T10:00:00",
                               ["The purple elephant walked in.", "Another sentence about a purple car and an elephant."])
        self.build()
        hits = self.find('"purple elephant"', use_vectors=False).hits
        self.assertEqual(len(hits), 1)
        self.assertIn("purple elephant", hits[0].text)

    def test_symbols_and_odd_queries_never_raise(self):
        for query in ('AI agents AND (harness*)', '"unbalanced', 'NEAR(a b)', "col:val", "a OR",
                      "x" * 5000, "kubernetes -pipeline", '"" "kubernetes"', "ünïcode wörds",
                      "a* OR (b AND NOT c)", "^kube", "kube\x00pipeline"):
            self.find(query)
        for query in ("'", "-", "***", '""', "   ", "\\"):
            with self.assertRaises(ConfigError, msg=query):
                self.find(query)

    def test_a_query_without_words_is_a_clear_error(self):
        with self.assertRaises(ConfigError):
            self.find("*** !!! ???")

    def test_results_come_only_from_the_users_library(self):
        self.world.add_episode(107, 2, "Only other has this", "2026-11-06T10:00:00",
                               ["Unique zeppelin content about airships."], users=("other",))
        self.build()
        self.assertNotIn(107, self.ids(self.find("zeppelin", user="owner")))
        self.assertEqual(self.find("zeppelin", user="other").hits[0].episode_id, 107)
        self.assertEqual(self.ids(self.find("sourdough", user="other")), {107})  # only episode they own

    def test_scope_also_limits_meaning_search(self):
        self.world.add_episode(107, 2, "Cars of the other user", "2026-11-06T10:00:00",
                               ["A vehicle, an automobile, a car, an auto."], users=("other",))
        self.build()
        owner = self.find("automobile", user="owner")
        self.assertNotIn(107, [h.episode_id for h in owner.hits])
        self.assertEqual(self.find("automobile", user="other").hits[0].episode_id, 107)

    def test_only_matched_episodes_are_searchable(self):
        self.world.add_episode(108, 2, "Needs review", "2026-11-07T10:00:00",
                               ["Findable quokka words."], match="needs_review")
        self.world.add_episode(109, 2, "Unmatched", "2026-11-08T10:00:00",
                               ["Findable wombat words."], match="unmatched")
        self.build()
        for query in ("quokka", "wombat"):
            self.assertFalse({108, 109} & self.ids(self.find(query)))
            self.assertFalse({108, 109} & self.ids(self.find(query, use_vectors=False)))

    def test_the_link_uses_a_video_from_the_users_library(self):
        # a second video for the same episode, in the other user's library only
        video_id = "vidOTHER0001"
        store.save_videos(self.conn, [video_id], [make_video(video_id, "dup", "2026-10-01T10:00:00", 600)], T0)
        self.conn.execute("INSERT INTO episode_matches (video_id, episode_id, status, resolved_at) "
                          "VALUES (?, 102, 'matched', ?)", (video_id, T0))
        self.conn.execute("INSERT INTO library_items (user_id, video_id, source, first_seen_at) "
                          "VALUES ('other', ?, 'liked', ?)", (video_id, T0))
        self.conn.commit()
        self.assertEqual(self.find("sourdough", user="owner").hits[0].url, "https://youtu.be/vid00000102?t=0")
        self.assertEqual(self.find("sourdough", user="other").hits[0].url, "https://youtu.be/vidOTHER0001?t=0")

    def test_filter_by_show_name_ignores_case_and_part(self):
        self.assertEqual({h.show for h in self.find("morning", show="greg").hits}, {"Greg Show"})
        self.assertEqual({h.show for h in self.find("morning", show="LENNY'S POD").hits}, {"Lenny's Podcast"})

    def test_an_ambiguous_show_name_lists_the_matches(self):
        self.world.add_episode(110, 3, "Daily thing", "2026-11-09T10:00:00", ["Daily morning news."])
        self.build()
        with self.assertRaises(ConfigError) as caught:
            self.find("morning", show="lenny")
        self.assertIn("Lenny's Daily", str(caught.exception))
        self.assertIn("Lenny's Podcast", str(caught.exception))

    def test_an_unknown_show_lists_the_users_shows(self):
        with self.assertRaises(ConfigError) as caught:
            self.find("morning", show="nonexistent")
        self.assertIn("Greg Show", str(caught.exception))

    def test_filter_by_date(self):
        # 101 is from Oct 1, 102 from Oct 15, 103 from Nov 1. Both search methods obey the dates.
        for vectors_on in (False, True):
            def got(vectors_on=vectors_on, **kw):
                return self.ids(self.find("morning", use_vectors=vectors_on, **kw))

            self.assertEqual(got(since="2026-10-20"), {103})
            self.assertEqual(got(until="2026-10-20") - {101}, {102})
            self.assertNotIn(103, got(until="2026-10-20"))
            self.assertEqual(got(since="2026-10-15", until="2026-10-15"), {102})
            self.assertEqual(got(since="2026-11-02"), set())

    def test_a_bad_date_is_a_clear_error(self):
        with self.assertRaises(ConfigError):
            self.find("morning", since="yesterday")

    def test_filter_by_episode_ids_and_combined_filters(self):
        self.assertEqual(self.ids(self.find("morning", episode_ids=[103])), {103})
        hits = self.find("morning", show="lenny", since="2026-10-20", episode_ids=[102, 103]).hits
        self.assertEqual({h.episode_id for h in hits}, {103})

    def test_at_most_three_chunks_per_episode_by_default(self):
        sentences = [f"Quokka fact number {i} about quokkas and their habits in the wild." for i in range(120)]
        self.world.add_episode(111, 1, "Quokkas", "2026-11-10T10:00:00", sentences)
        self.build()
        hits = self.find("quokkas", limit=20).hits
        self.assertEqual(len([h for h in hits if h.episode_id == 111]), retrieval.DEFAULT_PER_EPISODE)
        more = self.find("quokkas", limit=20, per_episode=6).hits
        self.assertEqual(len([h for h in more if h.episode_id == 111]), 6)

    def test_limit_is_respected_and_validated(self):
        self.assertEqual(len(self.find("morning", limit=1).hits), 1)
        for bad in (0, 51, -3):
            with self.assertRaises(ConfigError):
                self.find("morning", limit=bad)

    def test_nothing_relevant_returns_an_empty_or_weak_list_without_error(self):
        result = self.find("xylophone")
        self.assertIsInstance(result.hits, list)

    def test_a_user_with_no_library_gets_nothing(self):
        store.upsert_user(self.conn, "nobody", "UCn", "N", T0)
        self.assertEqual(self.find("kubernetes", user="nobody").hits, [])

    def test_ollama_down_at_search_falls_back_to_keywords_with_a_warning(self):
        self.embedder.fail_with = ApiError("Ollama stopped")
        result = self.find("sourdough")
        self.assertFalse(result.vectors_used)
        self.assertEqual(result.hits[0].episode_id, 102)
        self.assertTrue(any("keywords only" in w for w in result.warnings))

    def test_before_any_build_meaning_search_warns_and_keywords_find_nothing(self):
        fresh = store.connect(":memory:")
        store.upsert_user(fresh, "owner", "UCme", "Me", T0)
        World(fresh)
        result = retrieval.find(fresh, self.embedder, "anything", "owner")
        self.assertEqual(result.hits, [])

    def test_fusion_prefers_chunks_found_by_both_methods(self):
        fused = retrieval.fuse([1, 2, 3], [3, 4, 1])
        self.assertEqual([c for c, _ in fused][:2], [1, 3])
        self.assertEqual({c for c, _ in fused}, {1, 2, 3, 4})
        scores = dict(fused)
        self.assertAlmostEqual(scores[1], 1 / 61 + 1 / 63)

    def test_fusion_ties_go_to_the_keyword_order(self):
        fused = retrieval.fuse([5, 6], [6, 5])
        self.assertEqual([c for c, _ in fused], [5, 6])

    def test_get_chunk(self):
        hit = self.find("sourdough").hits[0]
        row = retrieval.get_chunk(self.conn, hit.chunk_id)
        self.assertEqual(row["episode_id"], 102)
        self.assertIsNone(retrieval.get_chunk(self.conn, 999999))


# ---------------------------------------------------------------------------- core and the command line


class CoreAndCli(Base):
    """Uses a real database file in the data folder, like the command line does."""

    def setUp(self):
        super().setUp()
        import os

        self.addCleanup(os.environ.pop, "PODCAST_RECALL_OLLAMA_URL", None)
        paths.ensure_data_home()
        self.file_conn = store.connect(paths.db_path(), paths.backup_dir())
        self.addCleanup(self.file_conn.close)
        store.upsert_user(self.file_conn, "owner", "UCme", "Me", T0)
        self.world = World(self.file_conn)
        self.world.add_episode(101, 1, "Shipping with Kubernetes", "2026-10-01T10:00:00", KUBE)
        self.world.add_episode(102, 2, "Bread Basics", "2026-10-15T10:00:00", BREAD)
        self.embedder = FakeEmbedder()
        self.services = indexer.IndexServices(embedder=self.embedder)

    def test_core_build_and_search_with_a_lock(self):
        result = core.build_index(conn=self.file_conn, services=self.services, now=self.now)
        self.assertEqual(result.indexed, 2)
        found = core.search_episodes("sourdough", conn=self.file_conn, services=self.services)
        self.assertEqual(found.hits[0].episode_id, 102)
        status = core.index_status(conn=self.file_conn)
        self.assertEqual(status.episodes_indexed, 2)
        self.assertEqual(core.get_chunk(found.hits[0].chunk_id, conn=self.file_conn)["episode_id"], 102)

    def test_a_second_index_build_is_refused_with_its_own_message(self):
        from podcast_recall.lock import SyncLock

        with SyncLock(paths.index_lock_path()), self.assertRaises(SyncAlreadyRunning) as caught:
            core.build_index(conn=self.file_conn, services=self.services, now=self.now)
        self.assertIn("index build", str(caught.exception))
        self.assertNotIn("sync", str(caught.exception).lower())

    def test_search_requires_a_known_user(self):
        from podcast_recall.errors import NotSignedIn

        with self.assertRaises(NotSignedIn):
            core.search_episodes("x", "nobody", conn=self.file_conn, services=self.services)

    def test_cli_search_prints_time_link_and_scores(self):
        import contextlib
        import io

        core.build_index(conn=self.file_conn, services=self.services, now=self.now)
        self.file_conn.commit()
        import os

        os.environ["PODCAST_RECALL_OLLAMA_URL"] = "http://127.0.0.1:9"  # nothing listens here
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli_main(["search", "sourdough starter", "--explain"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("Greg Show: Bread Basics", text)
        self.assertIn("0:00:00 to 0:00:14", text)
        self.assertIn("https://youtu.be/vid00000102?t=0", text)
        self.assertIn("keyword rank 1", text)
        self.assertIn("keywords only", err.getvalue())  # Ollama is not running: a warning, not a failure

    def test_cli_index_build_with_ollama_down_fails_clearly(self):
        import contextlib
        import io
        import os

        os.environ["PODCAST_RECALL_OLLAMA_URL"] = "http://127.0.0.1:9"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli_main(["index", "build"])
        self.assertEqual(code, 1)
        self.assertIn("Ollama", err.getvalue())

    def test_cli_rejects_a_non_loopback_ollama_address(self):
        import contextlib
        import io
        import os

        os.environ["PODCAST_RECALL_OLLAMA_URL"] = "http://192.168.1.5:11434"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli_main(["index", "status"])
        self.assertIn(code, (0, 2))  # status never calls Ollama, so the address does not matter
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli_main(["index", "build"])
        self.assertEqual(code, 1)
        self.assertIn("this computer", err.getvalue())

    def test_cli_status_and_no_results_message(self):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli_main(["index", "status"])
        self.assertIn("Waiting to be indexed: 2", out.getvalue())
        self.assertEqual(code, 2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            cli_main(["search", "kubernetes"])
        self.assertIn("No results.", out.getvalue())


# ---------------------------------------------------------------------------- the probe scorer


class ProbeScoring(IndexBase):
    def hit(self, episode_id, start, end):
        from podcast_recall.models import SearchHit

        return SearchHit(1, episode_id, "s", "t", start, end, "x", None, None, None, None, None, 0.1)

    def test_a_hit_counts_only_for_the_right_episode_and_time(self):
        from podcast_recall import probe

        hits = [self.hit(9, 100, 175), self.hit(5, 0, 75), self.hit(5, 60, 135), self.hit(5, 120, 195)]
        self.assertEqual(probe.gold_rank(hits, 5, 130), 3)  # the first chunk of episode 5 holding 130 s
        self.assertEqual(probe.gold_rank(hits, 5, 75), 2)  # boundaries are inclusive
        self.assertIsNone(probe.gold_rank(hits, 5, 500))
        self.assertIsNone(probe.gold_rank(hits, 8, 130))

    def test_recall_and_mrr(self):
        from podcast_recall import probe

        row = probe.ProbeRow("q", "v", 1.0, "", "")
        outcomes = [probe.ProbeOutcome(row, 1, []), probe.ProbeOutcome(row, 5, []),
                    probe.ProbeOutcome(row, 6, []), probe.ProbeOutcome(row, None, [])]
        self.assertEqual(probe.recall_at(outcomes, 5), 0.5)
        self.assertEqual(probe.recall_at(outcomes, 10), 0.75)
        self.assertAlmostEqual(probe.mean_reciprocal_rank(outcomes), (1 + 0.2 + 1 / 6) / 4)
        self.assertEqual(probe.recall_at([], 5), 0.0)

    def test_loading_the_probe_file_and_its_errors(self):
        import tempfile
        from pathlib import Path

        from podcast_recall import probe

        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        good = folder / "good.csv"
        good.write_text("question,video_id,gold_s,author,tag\nWhat?,abc,12.5,pm,raj\n\n", encoding="utf-8")
        rows = probe.load_probe(good)
        self.assertEqual((rows[0].video_id, rows[0].gold_s, rows[0].tag), ("abc", 12.5, "raj"))
        for name, text in (("a.csv", "question,video_id\nq,v\n"),
                           ("b.csv", "question,video_id,gold_s\nq,v,soon\n"),
                           ("c.csv", "question,video_id,gold_s\n,v,5\n")):
            (folder / name).write_text(text, encoding="utf-8")
            with self.assertRaises(ConfigError, msg=name):
                probe.load_probe(folder / name)

    def test_the_real_probe_file_loads(self):
        from pathlib import Path

        from podcast_recall import probe

        rows = probe.load_probe(Path(__file__).resolve().parents[1] / "data" / "retrieval_probe.csv")
        self.assertGreaterEqual(len(rows), 10)
        self.assertTrue(all(r.gold_s > 0 for r in rows))
        self.assertGreaterEqual(sum(1 for r in rows if r.tag == "raj"), 3)
