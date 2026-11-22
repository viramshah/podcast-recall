# Week 3: Answers and Chat, Plan (v2, 2026-11-21)

## Approach
1. **`llm.py`: the model client.** An Ollama chat client with schema-constrained output (`format`), loopback-only, explicit `num_ctx`, timeouts, one retry, and clear errors. Injectable, so no test needs Ollama.
2. **`units.py`: passage units.** Rebuild a chunk's units from the transcript segments: merge consecutive segments to about 5 to 15 seconds, never across a speaker change, each with an id and a start time. Pure and deterministic.
3. **`prompting.py`: the prompt.** The system rules and the numbered passages (with show, title and time range). Passages are delimited and described as untrusted text.
4. **`answering.py`: the path.** Search, number, ask, parse the model's JSON, map pointers to quotes (copy the text, cap at 60 words, take the unit's start time), build the `Answer`, hand it to the verifier, log, return.
5. **`verifier.py`: the production guard.** Wraps the Week 2 checkers R1 and R2, drops failing and uncited claims, caps the claims, sets `not_found` when nothing survives, and records why each claim was dropped.
6. **Migration `005_answers.sql`:** `answer_requests`, `feedback`, `findings`, with foreign keys to `users` and delete-on-cascade.
7. **`core.py`:** `ask`, `save_finding`, `record_feedback`, `list_findings`. No printing.
8. **`schemas.py` and `schemas/`:** typed models for every function's input and output, and generated JSON schemas, with a test that the published files match the models.
9. **`web.py` and `static/index.html`:** the FastAPI app, the safety checks (Host and Origin, the per-run token), the page with citation cards, thumbs and save finding. `podcast-recall serve`.
10. **`cli.py`:** `ask`, `serve`, and `eval answer`.
11. **`eval answer`:** answer the golden questions of a split against the evaluation library, write the answers and the scorecard CSV, and report status counts, drops and timings.
12. **README and tech stack:** the new settings and commands.
13. **Tests.** Units (merging, speaker changes, ids); the prompt (passages numbered, injected text delimited); the model path with a fake client (a good answer, a pointer to a missing unit, invalid JSON then retry then `not_found`, a refusal, a premise correction); the quote builder (copied word for word, capped at 60 words, correct time); the verifier (R1 and R2 failures dropped, an uncited claim dropped, the cap, `not_found` when nothing survives); a prompt-injection test; storage and cascade on `revoke`; the web layer (answers, Host and Origin checks refuse, the token is required, HTML is not interpreted, a bad video id is refused); the CLI; `eval answer` end to end with the fake client and the oracle-checkable guarantee that R1 and R2 never fail.

## Constraints
- Nothing reaches an LLM except passages from the user's own library and the question. No Spotify content (rule from the tech stack).
- Ollama only on loopback. The web app only on `127.0.0.1`.
- No secrets and no transcript or question text in log files. Question text is stored only in the private database.
- `core.py` has no printing. U1 to U4 and Week 2 are not changed, except additions to `core.py`, `cli.py` and the checker context.
- The golden set is not changed this week. Held-out questions are not used for tuning.

## New dependencies
None. The web layer is tested through a small ASGI helper in `tests/`, not FastAPI's test client, so `httpx` is not needed.

## Review checklist (PM)
- [ ] A question typed in the web chat comes back with citation cards, a `mm:ss` time and a link that opens at the right moment (checked on 5 answers)
- [ ] The same question on the command line gives the same answer
- [ ] A question that has no answer in the library says "I couldn't find that in your podcasts" and cites nothing
- [ ] A false-premise question gets a correction, not an invented reason
- [ ] The model's pointers become word-for-word quotes; none is written by the model
- [ ] A quote that cannot be verified never appears in an answer (tested by breaking the verifier's input)
- [ ] Ollama stopped gives a plain message, not a stack trace
- [ ] A web page on another origin cannot ask the local app a question
- [ ] Transcript text is displayed as text, never as HTML
- [ ] No question text and no transcript text in the log files; `revoke` removes requests, feedback and findings
- [ ] The baseline scorecard exists, with R1 and R2 failures at zero
- [ ] Nothing added beyond the spec (no judge, no reranker, no export, no conversation memory)
