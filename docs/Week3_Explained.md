# Podcast Recall

*Week 3 (answers, citation verifier, web chat and command line) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 22, 2026  |  Companion to docs/Week2_Explained.md, specs/decisions.md (D19) and specs/features/week3-answers-chat/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. It covers what Week 3 built, **why each decision was made**, what went wrong (again, a lot, and that is the useful part), what the first real scorecard says, and what to take from it as a PM.

## 1. What Week 3 is, in plain English

Weeks 1 and 2 built the library, the transcripts, the search and the yardstick. Week 3 builds **the thing that answers**. You type a question; the app finds the relevant passages, asks a local AI model to write a short answer, and shows each statement with a **word-for-word quote, a time, and a link that opens the video a few seconds before it**.

The hard part is not getting an answer. It is making sure **no quote is ever invented**. A model that is asked for a quote will sometimes write one that sounds right and was never said. For a product whose promise is "every answer is grounded and cited", one invented quote ends trust.

Week 3 delivers:

1. **An answering path** with a built-in citation check.
2. **A local web chat** (a page on your own computer) and a **command line** (`ask`) that share the same core.
3. **A baseline scorecard**: the first real measurement of the system against the Week 2 yardstick.

No accuracy target applies this week. The 90% gate is Week 4. This week's job is to get an honest number.

## 2. How an answer is made (and why it can't be faked)

| Step | What happens | Why |
|---|---|---|
| 1. Search | The Week 1d search finds the best few passages (about 2 minutes of transcript each), only from your library | Reuses what is already measured |
| 2. Number the pieces | Each passage is cut into short **units** of roughly 5 to 15 seconds and numbered U1, U2, ... | Gives the model something small and exact to point at |
| 3. Ask the model | The local model (Qwen 2.5, 7 billion parameters, via Ollama) sees the question and the numbered passages and replies with a short statement plus **which units support it** | The model chooses, it does not quote |
| 4. Copy, don't write | Our code copies the text of the chosen units and takes the time of the first one | A quote can only be real transcript text, and its time is exact to the unit |
| 5. Verify | The Week 2 rules R1 (quote really is in the transcript near that time) and R2 (the episode is in your library) are run again on every citation. Anything failing is removed | A second, independent check before you see anything |
| 6. Say "not found" | If nothing survives, you get "I couldn't find that in your podcasts." | An honest "no" beats a confident guess |

The key design choice is step 3 and 4: **the model returns pointers, never quotes.** That is why the scorecard shows zero fabricated quotes across 80 answers. It is also why a good deal of this week's trouble came from the model pointing at the wrong place.

## 3. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **Pointers, not quotes** | The model names unit numbers; code copies the words | A model cannot fabricate a quote it is not allowed to write |
| **Quote limits** | At most 2 sentences and 60 words; only units starting within 12 seconds of the first | Keeps the quote inside the checker's 15-second window |
| **Link opens 10 s early** | The video link starts 10 seconds before the quoted words | You hear the lead-in and the quote is not clipped |
| **Passages are untrusted data** | They sit between markers, marker-like text is defused, and the rules tell the model to ignore instructions inside a passage | A transcript could say "ignore your rules"; the verifier is the backstop if the model is fooled |
| **Two front ends, one core** | A web chat and a command line call the same functions | MCP, the usual way to plug into AI tools, is blocked by Qualtrics policy (D7), so this is the practical route |
| **Web chat is local only** | Listens on your own computer (127.0.0.1) only; checks the Host and Origin headers; needs a per-run token; the page only shows text, never HTML; links only for valid video IDs | The app has no login, so these checks are what keeps another website or program from using it |
| **Your questions stay private** | Questions are stored in your private database, never in log files; revoking your account deletes them | Questions can be sensitive |
| **A fake model for tests** | Tests use a stand-in model and stand-in search | Tests run in seconds with no network |
| **No new libraries** | Nothing was added to the project's dependencies | Fewer things to break or secure |

## 3b. What a "unit" is, and why it mattered

A **unit** is a piece of transcript of roughly 5 to 15 seconds, ending at a sentence end when there is one. Some publisher transcripts have no punctuation at all, so a unit is also cut at 15 seconds regardless. Units never cross a change of speaker.

Units are the smallest thing a citation can point at, so they set how precise a timestamp can be.

## 4. How we built it, and what went wrong (the useful part)

**The first fix: unit numbers restarted in every passage.** In a 3-question trial, 4 of the 7 claims were dropped because the model pointed at "a unit that does not exist". The prompt showed U1, U2, U3 in the first passage and U1, U2, U3 again in the second, and a 7-billion-parameter model mixed them up. The fix was to number units once across the whole prompt, so each number means exactly one place. The code now works out which passage a unit belongs to, so a wrong passage number from the model no longer matters.

**It looked like "I couldn't find that", but it was not a real refusal.** Two of three trial answers read "not found". They were answers whose every claim had been removed by the verifier, and an answer with no surviving claims turns into "not found". The checks had worked as designed. The answer had still been lost, which is a different problem from "nothing relevant exists".

**The web chat said "couldn't find" about free trials, and that was correct.** The web chat searches *your own library*, which currently holds a single episode. The free-trial content is in the **seed** episodes, which the command line reaches with `--seed`. Even there the speakers say **"pilot"**, not "free trial". Two lessons: check which library a tool is searching before blaming the model, and notice that a wording gap between a question and a transcript is a real retrieval problem. `serve` now also accepts `--seed`.

**It was far too slow, and the cause was not what I first guessed.** Answers took 85 to 160 seconds against a target of 15. I suspected memory pressure; `ollama ps` showed both models fully on the GPU. A speed test showed the model reads about 58 tokens per second and writes about 4, so a long prompt plus a multi-sentence reply takes minutes. Cutting from 8 passages to 4 helped; a smaller 3-billion-parameter model was faster but refused an answerable question. Later runs were faster (about 24 s median), probably a warm model and less competition for the machine.

**The first full run: 62%, with a clear pattern.** All 15 failures were the same rule: the system refused, or "corrected", a question it could have answered. Two causes showed up:
- 13 of 15 removed claims pointed at units that were **not consecutive** (the model cited units 3 and 5, skipping 4). Dropping them lost whole answers. They are now kept as separate citations, each still real text.
- The rule for correcting a false premise said "contradict **or do not support**". The model read that as permission to correct any question its passages only partly matched, and did so on 6 questions that had no false premise. The rule now says to use it only on a clear contradiction.

**The second full run: 68%, and a new problem.** The two fixes lifted accuracy from 62% to 68% and cut removed claims from 15 to 1. But the model now **never** uses the "premise corrected" answer, so false-premise questions went from 2 of 3 to 0 of 3. Narrowing a rule fixed one error and exposed the next. This is a classic prompt-tuning tradeoff, and it is why Week 4 needs a better mechanism than wording.

**A scorecard file was about to be committed with transcript text in it.** The answer files contain quotes. They are now excluded in `.gitignore`.

## 5. What the first scorecard says (dev split, 40 questions)

| Measure | Run 1 | Run 2 | Target |
|---|---|---|---|
| Grounded accuracy (R1, R2, R5, R7 only) | 62% | **68%** | 90% (Week 4) |
| Critical failures | 0 | 0 | 2% or less |
| R1 / R2 failures (invented or out-of-library quotes) | 0 | 0 | 0 |
| R7: timestamp within 15 s (20 timed questions) | 30% | 35% | reported only |
| Median time to answer | 31.9 s | 23.9 s | under 15 s |
| 90th percentile time | 76.3 s | 60.6 s | |

By type in run 2: single fact 10 of 13, synthesis 6 of 9, who/when 3 of 7, unanswerable 5 of 5, not-in-library 3 of 3, **false premise 0 of 3**.

**How to read it:**
- **The promise holds.** No answer in 80 contained an invented quote or a source outside your library. That was this week's real gate.
- **The system is too cautious, not too bold.** Every remaining failure is a refusal or a missed correction, never a made-up fact. This is the safer side to be on, and the score still has to rise.
- **Retrieval is the likely main cause.** About a third of answerable questions probably did not have the right passage among the four shown (Week 2 measured 70% recall). If the model never sees the answer, "not found" is honest. This is a hypothesis; Week 4 confirms it question by question.
- **The number can only fall once the judge arrives.** The deterministic rules cannot tell whether a claim actually answers the question. One answer cited a real quote about Google Flow in reply to a NotebookLM question. R3 (the judge) will catch that.

## 6. What to take from this as a PM

1. **A "no" has two causes.** "Not found" can mean "not there" or "the system lost it". Without logging why, you cannot tell them apart. The scorecard's "why claims were removed" line is what exposed the second kind.
2. **Constraints beat requests.** Telling a model "do not invent quotes" is a hope. Not letting it write quotes is a guarantee. Where a failure is unacceptable, design it out rather than ask it away.
3. **Small models get confused by small things.** Restarting numbering in each passage was enough to break citations. Make the format hard to misread.
4. **Fixing one error can expose another.** Narrowing the premise rule removed false corrections and the correct ones with them. Always re-measure everything you did not mean to change.
5. **Measure before blaming the usual suspect.** I guessed memory; the data said model speed. Check one fact (`ollama ps`, one speed test) before changing a design.
6. **Check what the tool is searching.** Half the "wrong answers" in the first demo were the right answer for the wrong library.
7. **Tune on the dev split, never the held-out one.** Both full runs used only dev questions. The held-out 20 are untouched for the Week 4 check.
8. **Be honest when the target is missed.** The 15-second target is not met on this machine, and it is recorded as such, with the options listed.

## 7. Still open

- **Latency:** median 24 s against 15 s. Options for Week 4: fewer or shorter passages, a smaller model, or a relaxed target for local use.
- **Refusals on answerable questions:** confirm whether retrieval is the cause, then fix retrieval first.
- **A reliable false-premise path:** wording alone has not worked on the 7B model.
- **The judge (R3, R4, R6):** needed so the score reflects whether claims answer the question.
- **Default number of passages:** 4 (faster) or 8 (more recall) in code; the runs used 4.
- **From Week 2, still unconfirmed by real people:** Jainam's real labels, questions written by you, and your read of the rubric.
- **Next: Week 4,** a hill-climb on retrieval, the judge, the false-premise path and speed, against the 120-question set.

## Glossary

| Term | Meaning |
|---|---|
| **Pointer** | A unit number the model gives to say "this supports my statement". The code, not the model, supplies the quote |
| **Unit** | A 5 to 15 second piece of transcript, numbered, the smallest thing a citation can point at |
| **Passage** | About two minutes of transcript returned by search, made of several units |
| **Verifier** | Code that re-runs the R1 and R2 checks on every citation and removes any that fail |
| **Prompt injection** | Text inside a document that tries to give the model orders; passages are treated as data to defend against it |
| **Seed episodes** | The 16 episodes used for development, reachable with `--seed` |
| **Local-only server** | A web page that only your own computer can reach, protected by Host, Origin and token checks |
| **ASGI** | The standard way a Python web app is called; tests call it directly instead of starting a server |
| **Tokens per second** | How fast a model reads or writes; the main driver of waiting time |
| **GPU** | The graphics chip that runs the model; "100% GPU" means the whole model fits there |
| **Grounded accuracy** | The share of answers passing the rubric (here, the code-checked rules only) |
| **R5 failure** | The system refused, or declined to correct, when it should have answered (or the reverse) |
| **Held-out split** | Questions never used for tuning, kept for the final check |
| **Judge model** | An AI model that grades what code cannot (does a claim answer the question). Built in Week 4 |
