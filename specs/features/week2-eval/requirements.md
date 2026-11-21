# Week 2: Evaluation First, Requirements (v2, 2026-11-18)

Branch: `feature/week2-eval` (from `main` after U4 was merged). Source: requirements doc sections 1.3 (metrics), 1.4 (rubric) and U8 (eval harness), and `specs/plan.md` Week 2. Decisions: D5 (rubric thresholds), D6 (second labeller), D11 (languages), D17 (retrieval). v2 adds the PM's answers to the 24 pre-build questions (all recommendations accepted), listed at the end and recorded as D18. D6 is decided: Jainam second-labels 20 items.

## Why eval comes first
The product promise is "every answer is grounded and cited". The gate is: at least 90% of golden-set answers pass the rubric, at most 2% contain a critical failure, and no fabricated citation reaches the user. None of that can be claimed, or improved, without a yardstick we trust. U4 showed the cost of skipping this: 10 questions said 90%, 20 said 70%, and two problems were in the measuring, not the product. Week 2 builds the yardstick before the answering code (U6) exists.

## What done looks like
- **Rubric v1.0:** one written, final version of the checks R1 to R7, with every threshold decided and every term defined, so two people (or a script and a person) grade the same way.
- **Golden set v0:** 60 questions over the seed library, each with a gold answer, the gold episode(s), and the gold time, labelled by the PM and mostly checked against the transcripts.
- **Agreement check:** a second person double-labels 20 items. Cohen's kappa is at least 0.7, or the ambiguous questions are rewritten and labelled again.
- **Deterministic checkers** for R1, R2, R5 and R7, as tested code, plus the answer format they check.
- **Harness skeleton:** a command that runs the checkers on a set of answers against the golden set and writes a scorecard (CSV), tested with an "oracle" answerer (copies the gold answer, must score 100%) and a "fabricator" (invents quotes, must fail).
- **Retrieval on the golden set:** recall@5 measured on the golden questions, replacing the 20-question probe as the retrieval yardstick.
- Cost: $0. No LLM is needed this week. The judge (R3, R4, R6) is calibrated in Week 4.

## Out of scope this week
- The answer model and the judge model (Week 3 and Week 4). Their choice is recorded later.
- Writing answers (U6), the citation verifier in production (U6), the web chat (U5).
- The HTML scorecard and the `make eval` release gate (Week 4), and growing the set to 120.

## The rubric, as it will be finalised (from requirements doc section 1.4)
An answer is **grounded** when every factual statement in it is backed by, and cited to, the transcript of an episode in the user's library. We measure faithfulness to the podcast, not whether the speaker is right. If a guest says something false, the answer attributes it ("Guest X claims...").

| # | Check | Method | Pass condition | If failed |
|---|---|---|---|---|
| R1 | Citation is real | Deterministic | Each cited quote matches the stored transcript (similarity at least 0.90, defined in Q7) inside the cited time window (plus or minus 15 s, Q8) | Critical |
| R2 | Source in library | Deterministic | Every cited episode is in this user's library | Critical |
| R3 | Claim support | LLM judge, calibrated | Each atomic claim is Supported, Partly, Unsupported or Contradicted against its cited chunk | Unsupported or Contradicted: Critical. Partly: Major (fails the answer, Q9) |
| R4 | Attribution | LLM judge | Each claim is attributed to the right speaker, show and episode | Wrong attribution: Critical |
| R5 | Abstention | Deterministic against the label | Unanswerable or false-premise question: says "not found" or corrects the premise | Invents an answer: Critical. Refuses an answerable question: Major |
| R6 | Completeness | LLM judge, 0 to 2 | Covers the key points of the gold answer | Minor (tracked, not gated) |
| R7 | Timestamp | Deterministic against the label | Cited start within plus or minus 15 s of the gold start | Separate metric |

Scoring: an answer PASSES with zero Critical and zero Major failures. **Grounded accuracy** = passes divided by questions. **Hallucination rate** = answers with at least one Critical, divided by questions. To clear the gate, three consecutive runs must all meet the targets (Week 4).

## What changed since the requirements doc was written
- **YouTube-first, Spotify deferred (D1).** The doc's "catalogue but not my library" question type is re-read as: an episode that is *indexed* but *not in the evaluation library* (Q17). `spotify_url` is dropped from the citation format until v1.1.
- **The library for evaluation is an explicit list of videos** (as `--seed` already allows in U4), not whatever the PM's YouTube account contains, so results are repeatable.
- **Retrieval is a measured component.** The golden set carries gold times, so recall@5 and the timestamp check (R7) come from the same labels.

## The answer format (a contract with U6)
The checkers need a structured answer. U6 will produce exactly this (proposed, Q13):
```
{
  "status": "answered" | "not_found" | "premise_corrected",
  "claims": [
    { "text": "...",
      "citations": [ { "video_id": "...", "episode_id": 123, "show": "...", "title": "...",
                       "quote": "(at most 2 sentences and 60 words)", "start_s": 1541.0,
                       "url": "https://youtu.be/<id>?t=1531" } ] }
  ],
  "summary": "optional one-paragraph answer text"
}
```
- R1 and R2 run on every citation. R5 reads `status`. R7 reads `start_s`.
- The link opens 10 seconds early (from the requirements doc), so `url` is `start_s` minus 10.

## The golden set (v0: 60 questions, Q14 to Q20)
Each item: `id`, `type`, `question`, `gold_answer`, `key_points`, `gold_evidence` (one or more `video_id@mm:ss`), `author`, `split` (dev or held-out), `tags` (for example `raj`), `notes`.

| Type | Requirements doc (120) | v0 (60) | Purpose |
|---|---|---|---|
| Single-fact lookup | 40 | 20 | A fact stated in one place |
| Cross-episode synthesis | 25 | 13 | What different guests said; tests attribution |
| Who / when said it | 20 | 10 | Tests timestamps and speaker |
| Unanswerable (on-topic, not in the library) | 15 | 7 | Tests abstention (R5) |
| False premise | 10 | 5 | "Why did X say Z?" when X never said it; must correct it |
| Indexed but not in the evaluation library | 10 | 5 | Must not cite it (R2) |

- **Corpus:** the 16 seed episodes. About 11 form the evaluation library and 5 are held back as "indexed but not in the library" (Q17).
- **Answerable questions** (single-fact, synthesis, who/when) must have evidence found in the transcripts. A helper checks the gold quote really is in the transcript at the gold time.
- **Unanswerable and false-premise questions** must be *verified absent*: a helper searches the transcripts for the key terms and flags any that appear (Q18).
- **Style:** natural wording that differs from the speaker's, at least a third written by the PM from memory (Q19). The Raj Shamani episodes (4 of 16) are included in proportion and tagged (D11).
- **Held-out split:** 20 of the 60 are never used for tuning, only for the final gate (Q20).
- **Labelling effort:** the assistant drafts candidates from the transcripts and the PM reviews and edits each (about 3 hours). The second labeller double-labels 20 (about 1 hour).

## Agreement (Cohen's kappa)
Before any answers exist, the second labeller independently labels 20 items. For each they give: (a) the question's type (answerable, unanswerable, false premise, not in library), (b) the gold episode(s), and (c) the gold start time. Kappa is computed on (a). Agreement on (b) and (c) is reported as a percentage (same episode; times within 15 s). The target is kappa at least 0.7. If lower: rewrite the ambiguous questions and label them again (Q5, Q6).

## The deterministic checkers (all pure functions, fully unit-tested)
- **R1:** for each citation, take the transcript text inside the cited window; normalise quote and text (lowercase, strip punctuation, collapse spaces); find the best-matching run of tokens of the quote's length; pass if the token similarity is at least 0.90 (Q7).
- **R2:** every cited `episode_id` is in the evaluation library.
- **R5:** `status` equals what the label requires (`not_found` for unanswerable, `premise_corrected` for false premise, `answered` otherwise). A false-premise answer that also contains claims asserting the false premise is flagged for the judge or the PM (Q11).
- **R7:** for single-fact and who/when items, the best-matching citation's `start_s` is within 15 seconds of a gold start. Synthesis items are checked at the episode level only (Q12).
- Each checker returns pass or fail with the reason, so every failure can be read.

## The harness skeleton
`podcast-recall eval run --answers FILE [--golden FILE] [--split dev|heldout|all]` reads answers (the format above) and the golden set, runs the checkers, and writes a scorecard CSV plus a console summary (accuracy, hallucination rate, per-type results, per-rule failures). `podcast-recall eval retrieval` measures recall@5 and MRR on the golden set using U4. `podcast-recall eval kappa --labels-a FILE --labels-b FILE` computes agreement. HTML scorecards, `make eval` and the release gate come in Week 4.

## Settings and files
Golden set and labels live in `data/golden/` (CSV, committed: private repo, short questions and gold quotes only). The evaluation library is `data/golden/eval_library.csv`. Scorecards go to `evals/scorecards/` (CSV, committed, so the history stays in the repo).

## Known risks
- **Labeller bias.** If the assistant drafts the questions, they inherit its phrasing and its sense of what is findable. Mitigation: the PM writes a third from memory, and the second labeller checks 20.
- **R1 checks the stored transcript, not the audio.** A Whisper error is invisible to it. Mitigation: spot-check by ear, tracked separately.
- **Small set.** 60 items, with 20 held out, is thin. Mitigation: report counts with every percentage and grow to 120 in Week 4.
- **Questions can become stale or ambiguous** as the library grows. Mitigation: ids are stable, and changes are logged.
- **The second labeller needs a way to find the answers.** Each item sits in a 60 to 140 minute episode. Without a searchable transcript, finding 20 answers could take several hours, not one. Transcripts are not shared (non-functional requirements), so the labeller uses the episodes themselves (YouTube's own transcript panel is searchable) and the PM decides what else to allow.

## Decisions made in the pre-build review (2026-11-18, all recommendations accepted)
1. Week 2 covers: rubric, golden set v0, deterministic checkers, kappa script, harness skeleton, retrieval recall on the golden set. The judge and the release gate come in Weeks 3 and 4.
2. The corpus is the 16 seed episodes.
3. The assistant drafts 60 candidate questions from the transcripts; the PM reviews each (about 3 hours).
4. D6: **Jainam** second-labels 20 items (decided 2026-11-18). **Met provisionally on 2026-11-20 by three cold model readers (kappa 1.00); Jainam has not labelled yet.**
5. Kappa is computed on the question type. Episode and time agreement are reported as percentages.
6. If kappa is below 0.7: rewrite the ambiguous items and label again.
7. R1 similarity: lowercase, strip punctuation, find the best-matching run of words of the quote's length inside the cited window, and require at least 0.90 word similarity (difflib ratio).
8. The window is 15 seconds either side of the cited time.
9. "Partly supported" fails an answer.
10. R5 reads an explicit `status` field (`answered`, `not_found`, `premise_corrected`).
11. A false-premise answer needs status `premise_corrected`. Every such answer is flagged for the PM to review.
12. R7 applies to single-fact and who/when questions. Synthesis questions are checked at the episode level.
13. The answer format is a list of claims, each with citations, plus the status. No Spotify links until v1.1.
14. The golden set is one CSV in `data/golden/`, with the evidence as `video@mm:ss`.
15. Fields: id, type, question, gold_answer, key_points, gold_evidence, author, split, tags, notes.
16. The v0 mix of 60: 20 single-fact, 13 synthesis, 10 who/when, 7 unanswerable, 5 false premise, 5 not-in-library.
17. 11 episodes form the evaluation library (`data/golden/eval_library.csv`); 5 are held back as "indexed but not in the library" (`data/golden/held_out_episodes.csv`). The assistant proposed the split and the PM can veto it. Rule used: a held-out episode's topic must be distinct from every library episode, so a "not in the library" question cannot be answered legitimately from the library. Held out: Diet Expert (Raj Shamani), Inside the black box of AI, Meta's Muse, Why PMs are suddenly valuable again (all Lenny's), and The 9 Stages of AI Agent Adoption (Greg Isenberg). Library: Gita Gopinath, Sachin Puri and Vinh Giang (Raj Shamani, 3 of the 11); Josh Woodward, Jen Abel and Rob Snyder (Lenny's); and five Greg Isenberg episodes.
18. A script checks that each gold time exists in its transcript and that unanswerable and false-premise items are absent from the transcripts.
19. Natural wording that differs from the speaker's; at least a third written by the PM from memory (**met in numbers on 2026-11-20 by a stand-in: 20 of 60 are authored `pm_proxy`; 8 by the reviewer agent and 32 by the assistant; none by the PM himself**); the Raj Shamani episodes included in proportion and tagged `raj` (D11).
20. 20 of the 60 are held out and never used for tuning.
21. Checkers are pure functions returning pass or fail with a reason, tested with an oracle and a fabricator.
22. Recall@5 on the golden set replaces the 20-question probe; the probe file stays for history.
23. Scorecard: CSV and a console summary now; HTML in Week 4.
24. The answer and judge models are chosen in Weeks 3 and 4 and must come from different model families.

## Details settled while writing v2
- An unparseable answer (wrong structure) counts as a failed answer with reason `format`.
- A claim with no citation fails R1 ("uncited claim").
- R2 also checks that a citation's video belongs to its episode.
- For not-in-library and unanswerable questions the expected status is `not_found`, and the claims list must be empty.
- A missing answer for a golden item counts as a failure (Major, "no answer").
- **A quote is at most 2 sentences and at most 60 words** (found on 2026-11-18: some publisher transcripts have no punctuation, so "2 sentences" alone cannot limit a quote; the oracle's own quote ran to 2,390 words until this was fixed). U6 must respect both limits.
- Until the judge exists, the scorecard says clearly that it covers the deterministic rules only (R1, R2, R5, R7) and not R3, R4 or R6.
