# Evaluation rubric v1.0 (2026-11-18)

This is the rubric the evaluation uses. It replaces the draft in section 1.4 of the requirements document. Thresholds are decision D5 (provisional until real answers exist). The checks R1, R2, R5 and R7 are code (`podcast_recall/checkers.py`). R3, R4 and R6 need a model and are calibrated in Week 4.

## What "grounded" means
An answer is **grounded** when every factual statement in it is backed by, and cited to, the transcript of an episode in the user's library. We measure faithfulness to the podcast, not whether the speaker is right. If a guest says something false, the answer attributes it ("Guest X claims...").

## The answer an evaluator sees
`status` is `answered`, `not_found` or `premise_corrected`. An answer is a list of **claims**; each claim has one or more **citations**. A citation has the episode, a **quote of at most 2 sentences and 60 words**, the time the quote starts, and a link that opens 10 seconds early.

## The checks
| # | Check | Method | Passes when | If it fails |
|---|---|---|---|---|
| R1 | Citation is real | Code | Every claim has a citation, and each quote matches the stored transcript within 15 seconds of the cited time at 0.90 word similarity or better | **Critical** |
| R2 | Source in library | Code | Every cited episode is in the user's library, and each cited video belongs to its episode | **Critical** |
| R3 | Claim support | Judge model | Each atomic claim is Supported by its cited quote | Unsupported or Contradicted: **Critical**. Partly: **Major** |
| R4 | Attribution | Judge model | Each claim is attributed to the right speaker, show and episode | Wrong attribution: **Critical** |
| R5 | Abstention | Code | The status matches the question type (below) | Invented answer: **Critical**. Refusal of an answerable question: **Major** |
| R6 | Completeness | Judge model, 0 to 2 | The answer covers the gold key points | Minor, tracked, not gated |
| R7 | Timestamp | Code | A citation to the gold episode starts within 15 seconds of the gold time | Reported separately; never fails an answer |

**An answer PASSES with no Critical and no Major failure.** "Partly supported" fails an answer (it is Major).
- **Grounded accuracy** = passing answers divided by questions asked.
- **Hallucination rate** = answers with at least one Critical failure divided by questions asked.
- **The gate:** at least 90% grounded accuracy, at most 2% hallucination rate, and zero fabricated citations reaching the user, in **three consecutive runs**.

## Definitions
- **Word similarity (R1).** Lowercase, remove punctuation and curly quotes, split into words. Take the words of every transcript segment that overlaps the 15 seconds either side of the cited time. Slide a window of about the quote's length over those words and take the best match: similarity is `2 x matching words / (words in quote + words in window)`. One changed word in a ten-word quote scores 0.90, which passes. Two changed words score 0.80, which fails. A quote that is simply shortened still matches.
- **In the library.** The evaluation library is the explicit list in `data/golden/eval_library.csv`, not the user's whole account.
- **Expected status by question type.** `single_fact`, `who_when`, `synthesis`: `answered`. `unanswerable` and `not_in_library`: `not_found` with no claims. `false_premise`: `premise_corrected`. A false-premise answer is always read by a person.
- **Missing or malformed answers** fail the question: no answer is Major, a malformed answer is Major with the reason `format`.

## Worked examples (real questions from the golden set)
**R1, a pass.** Question `sf01`: "What can push inflation away from a central bank's target?" Cited at 10:30 (Gita Gopinath episode) with the quote "what can generate inflation deviating from target? It could be that there is so much of a boom in demand in the economy". The quote is in the transcript within the window. Similarity 1.0. **Pass.**

**R1, a fail (fabricated).** Same question, same time, quote "The guest firmly declared that the moon landing was scheduled for next Tuesday." Nothing in the window matches. Similarity under 0.2. **Critical. The answer fails.**

**R1, a fail (uncited).** A claim "Inflation is caused by demand" with no citation attached. **Critical: "claim 1 has no citation".**

**R1, the edge.** Quote "A good pipeline has staging, checking and a rollback plan" against a transcript that says "review" where the quote says "checking". Nine of ten words match: similarity 0.90. **Pass, exactly at the threshold.** With two words changed it is 0.80. **Fail.**

**R2.** Question `nl03`: "Why did the Meta team keep the Jolly avatar instead of a corporate logo?" The only episode that answers it (Meta's Muse) is indexed but **not in the evaluation library**. An answer that cites it, with a perfectly real quote, **fails R2 (Critical)**. The correct answer is `not_found`.

**R5, the right behaviour.** Question `un03`: "What did Gita Gopinath say about Bitcoin and stablecoins?" Neither word appears in any episode. Status `not_found` with no claims: **Pass.** An answer with status `answered` and any claim: **Critical (invented an answer).**

**R5, a refusal.** Question `sf01` answered with `not_found`: the answer exists, so this is a refusal: **Major. The answer fails, but it is not a hallucination.**

**R5, a false premise.** Question `fp04`: "Why did Gita Gopinath say the IMF has defaulted on its loans?" She says the opposite, that nobody has ever defaulted to the IMF. The right status is `premise_corrected`. It passes the code check and is **always flagged for a person to read**, to confirm the correction is itself accurate.

**R7.** Question `sf09` has a gold time of 25:44. A citation to the same episode at 25:55 is 11 seconds off: **within the 15 second tolerance**. A citation at 26:10 is 26 seconds off: **R7 fails**, reported in the timestamp metric. If the quote is real, R1 still passes, because R1 checks the quote against the time the answer cites.

## What these checks do not catch
- **R1 checks the stored transcript, not the audio.** A Whisper error is invisible to it. Spot-check by ear.
- **A real quote can still be used to say something the speaker did not mean.** That is R3, the judge model's job, and a person grades R3 by hand if the judge and humans agree on under 85% of items.
- **R5 for false premises** only checks the status. Whether the correction is itself right is read by a person.

## Rules for using the golden set
- Questions are marked `dev` or `heldout`. **Held-out questions are never used for tuning**, only for the final gate. Reports always show the two splits separately.
- Report counts with every percentage. A change of one question is 1.7 points on 60 questions.
- Do not edit a question after seeing a system's answer to it. Add a new question and retire the old one with a note.

## Version history
- v1.0 (2026-11-18): thresholds from D5 accepted as provisional: 0.90, 15 seconds, "Partly" fails. Quote limits added (2 sentences and 60 words). Unpunctuated transcripts were the reason for the word limit.


## Clarification (D21, 2026-11-23): speaker names
R3 judges whether the cited quote says what the claim says, ignoring who is named. R4 judges whether the named speaker, show and episode are right, using the transcript's speaker label or episode metadata rather than the quote text. A name the quote lacks is not an R3 failure; a name nothing in the episode supports is an R4 failure. A detail the quote lacks (a cause, number or recommendation) is an R3 failure.
