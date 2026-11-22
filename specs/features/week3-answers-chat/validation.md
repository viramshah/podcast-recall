# Week 3: Answers and Chat, Validation (v2, 2026-11-21)

Run these yourself before merging. Ollama must be running with `qwen2.5:7b-instruct` and `nomic-embed-text`.

## Automated
1. `make test` passes, including the verifier, quote builder, injection, web-safety, storage and `eval answer` tests.
2. `make lint` is clean.

## Manual
| # | Step | Expected |
|---|---|---|
| 1 | `make test && make lint` on your machine | Passes |
| 2 | `podcast-recall ask "<a question about one episode>" --seed` | An answer with 1 to 5 claims, each with a quote, a `mm:ss` time and a link; no claim without a citation |
| 3 | Open 5 of the links | Each opens within about 15 seconds of the quoted words |
| 4 | Ask something that is in none of the episodes | "I couldn't find that in your podcasts", no citations |
| 5 | Ask a false-premise question (for example "Why did Jen Abel say you should never offer a free trial?") | A correction that says what she did say, not an invented reason |
| 6 | `podcast-recall serve`, open `http://127.0.0.1:8000`, ask the same question as step 2 | The same answer, shown as citation cards |
| 7 | Click thumbs up on one answer and thumbs down on another; click "save finding" on one | Each is stored (`answer_requests`, `feedback`, `findings`) |
| 8 | From a terminal, send a request with a bad `Origin` header, then without the token | Both are refused |
| 9 | Stop Ollama and ask | A plain message about Ollama, no stack trace |
| 10 | `podcast-recall eval answer --split dev` | A scorecard and an answers file. R1 and R2 failures are zero. Status counts, claims dropped and why, median and 90th percentile time reported |
| 11 | Compare the median time with the 15 second target | Recorded, even if above target |
| 12 | Measure `llama3.1:8b` speed with one question (an open Week 0 item) | The tokens per second are recorded, for the Week 4 judge choice |
| 13 | Search the log files for a phrase from your questions and from a transcript | Nothing found |
| 14 | `uv run podcast-recall revoke --user <a test user>` on a copy of the data | The user's requests, feedback and findings are gone |
| 15 | `git status`, and a search for secrets | No audio, transcript or database files tracked. No secrets |

## Record the results
The scorecard (status counts, drops, timings, R1 to R7 as far as they run), the latency, the llama3.1 speed, and every change to the spec in `results.md` and `decisions.md`.

## Exit gate
The web chat and the command line both give a cited answer and a working link, the baseline scorecard exists with zero R1 and R2 failures, and the review checklist in `plan.md` is ticked. Then update `decisions.md` and the roadmap, write `docs/Week3_Explained.md`, and merge.
