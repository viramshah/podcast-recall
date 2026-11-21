# Podcast Recall

*Week 2 (evaluation first) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 20, 2026  |  Companion to docs/Week1d_U4_Explained.md, specs/decisions.md (D5, D6, D18) and specs/features/week2-eval/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. It covers what Week 2 built, **why each decision was made**, what went wrong (a lot went wrong, and that is the useful part), what is still unconfirmed by real people, and what to take from it as a PM.

## 1. What Week 2 is, in plain English

The promise of Podcast Recall is: **every answer is grounded in your podcasts and cited.** The roadmap says that is only a claim until you can measure it, with a target of at least 90% of answers passing, at most 2% containing a serious failure, and no fabricated citation ever reaching you.

Week 2 builds the **yardstick before the thing it measures**. No answering code exists yet (that is Week 3). What exists now is:

1. **A rubric:** the written rules for what counts as a good answer.
2. **A golden set:** 60 questions with known answers, over your 16 seed episodes.
3. **Automatic checkers:** code that applies four of the rubric's rules without any AI model.
4. **A harness:** a command that grades a pile of answers and writes a scorecard.
5. **An agreement check:** a way to tell whether two people read the questions the same way.
6. **A retrieval baseline:** how well search finds the right passage for each golden question.

Why first? Week 1d (U4) already showed the danger of skipping this. Ten questions said 90%, twenty said 70%, and two of the problems were in the measuring, not the product.

## 2. The rubric, in everyday words

An answer is **grounded** when every statement in it is backed by, and cited to, a transcript of an episode in your library. We measure faithfulness to the podcast, not whether the speaker is right. If a guest says something false, the answer should say "the guest claims...".

| Rule | Plain meaning | Who checks it | If it fails |
|---|---|---|---|
| **R1** | The quote is really in the transcript, near the time the answer cites | Code | Critical |
| **R2** | The cited episode is in your library | Code | Critical |
| **R3** | Each claim is actually supported by its quote | A judge model (later) | Critical or Major |
| **R4** | The right speaker and episode are credited | A judge model (later) | Critical |
| **R5** | When the question can't be answered, it says so (and corrects a false premise) | Code | Critical (invented an answer) or Major (refused a question it could answer) |
| **R6** | The answer covers the key points | A judge model (later) | Minor, not scored |
| **R7** | The cited time is within 15 seconds of the true time | Code | Reported separately |

An answer **passes** with no Critical and no Major failure. Only R1, R2, R5 and R7 are built, because they need no model. Every scorecard says so plainly, so the numbers can only get worse once the judge rules arrive.

## 3. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **D5: how close a quote must be** | 0.90 word similarity, within 15 seconds either side of the cited time, and "partly supported" fails an answer | A quote must be nearly word-for-word, or it cannot be checked. One changed word in ten still passes (exactly 0.90); two fail. These values stay provisional until real answers exist. |
| **Rules as code, not opinion** | R1, R2, R5, R7 are plain functions that return pass or fail *and the reason* | A failure you cannot read is a failure you cannot fix. Code gives the same verdict every time and costs nothing to run. |
| **A fixed answer format** | Each answer has a status (`answered`, `not_found`, `premise_corrected`) and claims with citations. A quote is at most 2 sentences **and 60 words** | The checkers need structure. The status field lets R5 test "did it say not found?" without guessing from wording. |
| **The library is an explicit list** | 11 episodes are "in the library"; 5 are "indexed but outside it" | Results must be repeatable, not depend on whatever your YouTube account holds. The 5 outside episodes test that the system never cites something you haven't saved. |
| **Six question types** | 20 single-fact, 13 synthesis, 10 who/when, 7 unanswerable, 5 false premise, 5 not-in-library | Each type tests a different skill. Half the types test *not* answering when it should not. |
| **Held-out questions** | 20 of the 60 are never used for tuning, only for the final check | If you tune a system on the very questions you grade it on, it learns the test. Keeping some aside is the only honest way to tell whether an improvement is real. |
| **Test with an oracle and a fabricator** | An "oracle" builds perfect answers (must score 100%). A "fabricator" makes six kinds of wrong answers (each must fail the right rule) | Before you trust a thermometer, check it reads 0 in ice water and 100 in boiling water. |
| **Agreement measured by kappa** | A second person labels 20 items; kappa (a chance-corrected agreement score) must reach 0.7 | If two readers disagree on what a question is asking, the question is ambiguous and the score means nothing. |
| **No AI model needed yet** | The judge model is chosen in Weeks 3 to 4, from a different family than the answering model | A judge from the same family tends to favour its own style. |

## 4. How we built it, and what went wrong (the useful part)

This was the most correction-heavy stretch so far. Each item below is a lesson.

**The first oracle run scored 92%, not 100%.** The oracle builds a quote by adding transcript segments until it has two sentences. The AI Agents Full Course transcript has **no punctuation**, so it never found a second sentence and ran on for **2,390 words (14 minutes)**. The harness caught a bug in the thing built to test the harness. The fix was twofold: bound the oracle, and cap every quote at 60 words, because "2 sentences" cannot limit a quote on an unpunctuated transcript. That limit now applies to the future answering code too.

**Cold-open teasers fooled my own gold times, twice.** Many episodes open with a short preview of lines repeated later. When I located an answer by searching for a phrase, the first match was sometimes the preview, minutes before the real discussion (`sf07` and `sy10`). I added a check that warns when evidence sits in the first three minutes of a long episode.

**My "verified absent" questions weren't.** I told you `un03` (stablecoins) was confirmed absent. It wasn't: the transcript says "stable coin" as two words, and I'd searched for one. A fresh reviewer also found a library episode naming video editing software (my search only looked for names I already knew), and a free pilot that made one false-premise question's answer incomplete. I now check absence per episode, with spelling tolerance.

**An independent reviewer found real flaws, and I checked its claims before believing them.** A fresh agent reviewed all 60 questions: **36 keep, 4 edit, 20 replace**. I verified its main claims against the transcripts, and they held. It also found redundancies I hadn't noticed: three questions testing the same passage, and one repeating another.

**Its fix overcorrected, and I caught that.** Its 20 replacements pushed the Raj Shamani share from 28% to 45%. I swapped nine for questions about the other shows (back to 30%) and verified each new one against the transcripts. One of my own gold answers had to be reworded because the transcript's sentence was garbled.

**A tooling number was misleading.** The time-agreement figure between labellers read 62%, because it mixed in questions whose time is never scored. On the ten questions where time **is** scored, agreement was 100% and later 80%. The command now reports only the scored types, with the item count.

**Models stood in for people, and that is recorded as what it is.** You asked me to fill in the second labeller (Jainam) and your own questions. I could do the mechanical parts, but not honestly present them as a human gate. So:

- **"Jainam":** three fresh agents, each told not to look at the answers (and each reporting that it did not; I cannot verify that), labelled the question types. All three matched on every one of 20 (kappa 1.00). My own earlier attempt does not count, because I wrote the answers.
- **"Viram":** a fresh agent wrote 20 questions in a listener's words; I verified them and corrected two gold answers. They are authored `pm_proxy`.
- The result: **the numbers are met, but a model produced them.** The files, the decision log and the roadmap all say so.

## 5. Where retrieval ended up

The baseline on the full golden set:

| Measure | Result | Target |
|---|---|---|
| Recall@5 (30 questions with a gold time) | **70%** | 85% |
| Recall@10 | 70% | |
| MRR | 0.57 | |
| Synthesis: episodes found in the top 5 | 78% | |
| Results from outside the library | **0** | must be 0 |

The most useful detail: **recall@10 equalled recall@5**, so the nine misses were not near-misses. The right chunk was outside the top 10 altogether. A reranker, which only re-orders what is already in the list, would not fix that. So I added a diagnosis, and it found a pattern:

| Group | Questions | What was happening |
|---|---|---|
| **A. Openings crowd out the answer** | 7 of 9 | Each episode starts with a teaser and a host summary of everything to come. That reads like a table of contents and matches almost any question. With only 3 chunks per episode allowed, it used up the slots. |
| **B. A chunk-boundary near miss** | 1 | The returned chunk starts 36 seconds after the gold time and covers the same passage. |
| **C. A wording gap** | 3 (one overlaps A) | The question's words don't resemble the transcript's. |

**The experiment, run properly.** Demoting an episode's opening on the **dev** split moved recall@5 from **65% to 85%**, and it plateaued from 0.5 down to 0. A finer sweep showed any demotion gives 80% and 0.5 gives 85%. I fixed **0.5** as the value *before* looking at the held-out split.

**Then the held-out check, run once:** recall stayed at **80%** with or without the demotion (MRR 0.68 to 0.70). It wasn't confirmed. That is not a refutation: the held-out control was already at 80%, and its two misses are wording gaps, so held-out had no question of the kind the fix addresses. By the rule I set in advance, the **default stays off**, and the weight is available as a setting (`PODCAST_RECALL_INTRO_WEIGHT`). Week 4's 120-question set will decide.

## 6. What to take from this as a PM

1. **Test the measuring stick first.** The oracle caught an oracle bug; the reviewer caught absence checks that weren't; a misleading agreement number turned out to mix scored and unscored questions. Most of the real problems were in the yardstick, not the product.
2. **Verify claims, including your own and a helper's.** I had said `un03` was verified. A reviewer said `un07` was flawed. Both needed checking against the transcripts, and I was wrong once in each direction.
3. **Don't tune on the test.** Keeping a held-out slice meant that when an improvement didn't carry over, we knew, and didn't ship a guess.
4. **An inconclusive result is a result.** Held-out had no cases the fix addresses. Saying "this can't confirm or refute it" is more useful than calling it a win or a failure.
5. **Be honest about stand-ins.** A model reading a question cold is real evidence that the question is clear. It isn't a human's agreement, and it isn't your voice. Record it as what it is, and decide later whether to ask the real people.
6. **Teasers and unpunctuated text are traps.** Anything that repeats content out of place (an intro preview) or breaks an assumption (no sentence ends) will quietly mislead a search, a checker, or a human reviewer.

## 7. Still open

- **Jainam's real labels** on the frozen 20-question sheet. Do not regenerate that sheet: the sampling depends on the question ids and would now pick different questions.
- **Questions written by you.** None of the 60 is yours; 20 are `pm_proxy`. Before testers join (Week 6), or before quoting any result outside the project, add or swap a handful of your own.
- **Your read of the rubric:** would you grade the same way?
- **The retrieval target (85%)** is not met: 70% overall. Week 4's hill-climb covers the opening-weight decision, wording gaps and a reranker.
- **Week 3 comes next:** U6 (the answers and the citation verifier that blocks fabricated quotes) and U5 (the web chat and command line).

## Glossary

| Term | Meaning |
|---|---|
| **Golden set** | A hand-checked list of questions with known answers, used to grade the system |
| **Rubric** | The written rules for what counts as a good answer (R1 to R7) |
| **Grounded** | Every statement is backed by, and cited to, a transcript in the library |
| **Critical / Major failure** | A fabricated or wrongly sourced answer, or one that refuses a question it could answer. Any of them fails the answer |
| **Oracle** | A test answerer that builds perfect answers from the golden set. It must score 100% |
| **Fabricator** | A test answerer that makes deliberate mistakes. Each kind must fail the right rule |
| **Held-out split** | The 20 questions never used for tuning, kept for the final check |
| **Abstention** | Saying "not found" (or correcting a false premise) when the question cannot be answered |
| **False premise** | A question that assumes something nobody said ("Why did X say Y?") |
| **Cohen's kappa** | An agreement score between two labellers, corrected for chance. 1.0 is perfect; 0.7 is the gate |
| **Judge model** | An AI model that grades the parts code cannot (support, attribution, completeness). Built later |
| **Cold open (teaser)** | The short preview of lines at the start of an episode, repeated later |
| **Recall@5** | The share of questions where the right passage is in the top 5 search results |
| **MRR** | How high the right passage ranks on average (1.0 means always first) |
| **Stand-in** | A model playing a person's role (Jainam or Viram). Useful evidence, recorded as such, not a human confirmation |
