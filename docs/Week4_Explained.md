# Podcast Recall

*Week 4 (the hill-climb: finding out why answers fail, fixing what can be fixed, and an honest score) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 26, 2026  |  Companion to docs/Week3_Explained.md, specs/decisions.md (D20 to D24) and specs/features/week4-hillclimb/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. Week 4 is the week the project met reality. It built the tools to measure answer quality honestly, found that the score the code can see (78%) is far above the score a careful reader gives (35 to 40%), fixed what it could, and ended with a decision to change what the release gate means. This guide says plainly what is solid, what is not, and why.

## 1. What Week 4 was for

Week 3 ended with a baseline: 62 to 68% on the rules the code can check, and a list of problems. Week 4's job was to **raise accuracy to the gate: at least 90% grounded and at most 2% hallucination, on three runs in a row.** The method was fixed in advance (D20): find out *why* each question fails, change one thing at a time, keep the change only if a rule written before the run says it helped, and look at the held-out questions only three times.

**What happened, in one paragraph.** The system never invents a quote or cites a source outside your library (zero failures in every run). It got much better at answering questions it used to refuse (a bigger model fixed all four), and a new rule stopped it answering about episodes that are not in the library. But a careful reader found that about **four in ten answered questions contain a claim that says more than its quote**, so the 90% gate was not met, and we changed what the release gate measures (D22). Everything below explains how we know that, and what each experiment taught.

## 2. How we found out why answers fail

Before changing anything, Week 4 built a diagnosis tool. For each failing question it checks, in order, whether the right passage was even shown to the model, whether the model refused anyway, whether it was a false-premise question, and so on. The first diagnosis of 40 dev questions found 13 failures: 6 where the right passage was not among the four shown, 4 where it was shown and the model still said "not found", and 3 false-premise questions.

**Why this order matters:** it stops you "fixing" the model when the real problem is search. Half the early failures were search, not the model.

## 3. The experiments (12 of 13 used)

Each experiment had a keep rule written before the run. A table is the clearest way to see them:

| # | What we tried | Result | Why |
|---|---|---|---|
| E1 | More rules and worked examples in the prompt | **Reverted** | Two controls that used to pass regressed; the small model did not use the examples |
| E2 | A different answer model (llama3.1:8b) | Not adopted | It pointed at wrong units; no better |
| E3 | Decide "answer or not found" from search distance alone | Partial | Separated not-in-library questions only; too crude for the rest |
| E4 | A cautious checker model after the answer | Not adopted | It dropped 70 of 74 claims, including good ones; exposed that the judge was the real problem |
| E5a | Show the model only the 12 best units | Opt-in only | Halved the prompt on the 7B model, but cost accuracy at the margin |
| E6 | Demote the first minutes of each episode in search | Kept | One more question right; a teaser at the start of an episode often matches too well |
| E7 | Wide search, narrow prompt | **Reverted** | Worse (24 of 40 against 28) |
| E8 | **A bigger model: `qwen2.5:14b-instruct`** | **Kept** | Fixed all four refusals that five 7B experiments could not; 85% on the 20-question subset |
| E9 | A separate false-premise step | Not adopted | Fixed the 3 targets, but turned 3 unanswerable questions into wrong "corrections" |
| E10 | Stricter rules for writing claims | **Reverted** | Claims got shorter, but the share fully supported did not move (47.5% to 48.5%) |
| E11 | 14B model with unit selection, for speed | Opt-in only | Time halved (149 s to 75 s) but two answerable questions were now refused |
| E12 | **One rule: if the question names a specific episode, video, show, product or team that no passage mentions, say "not found"** | **Kept** | Fixed the two wrong answers about episodes not in the library; zero new damage beyond one retrieval miss |

**The most useful lesson in the table:** five experiments on the 7B model changed the score by one to four questions each, which on a 20-question subset is inside the noise. The single big gain came from changing the *model*. When small adjustments do not move a number, the limit is usually a capacity, not a wording.

## 4. The judge that did not qualify

A "judge" is a second AI model that grades what code cannot: does the quote actually say what the claim says? We tested it against labels on 60 claims, with a rule written in advance: at least 85% agreement on pass/fail and kappa of at least 0.6.

| Judge | Agreement on pass/fail | Kappa | Bar |
|---|---|---|---|
| llama3.1:8b | 68% | 0.19 | 85% / 0.6 |
| qwen2.5:14b | 80% | 0.24 | 85% / 0.6 |

Neither qualified, so the judge is **not** used for gating. The first judge was far too lenient (it said "supported" on 41 of 60 claims; the labeller said 20). The sample was also weak: the labeller passed only 5 of 60, so there were too few positive cases for a stable score.

**A subtler point: the labels were made by models, not by you.** Every grading in this week came from blind AI agents acting as a fresh reader, because a human grading was not available in time. Three independent readers agreed closely (exact agreement of 25 to 29 of 30 per pair; the same four claims marked "no" by all three). That makes the finding stable. It does **not** show that the readers match a person. You waived that check (D23), and every number that depends on it is labelled "model-graded, no human check".

## 5. The honest score

There are two scores, and the gap between them is the main finding of the week.

| | Dev (80 questions) | Held-out (40 questions) |
|---|---|---|
| **What the code can see** (quote is real, source in library, abstention correct) | 79% grounded | 78% grounded |
| **What a careful reader sees** (claims fully supported by their quotes, strict rule) | **35%** | **40%** |
| Answered questions with an unsupported claim | 37% | 48% |
| Invented or out-of-library citations | **0** of 80 | **0** of 40 |

**Why they differ.** The code proves a quote is real and sits in the right episode. It cannot see whether the sentence the model wrote *about* the quote goes beyond it. Typical problems found by the readers: a timestamp or number that is not in the quote, a "when" question answered with a "what", a quote cut off before its key phrase, advice drawn from a hypothetical example, and a name the episode does not support.

**Held-out was not worse than dev.** That is good news: the settings tuned on dev did not overfit.

**Fresh questions were worse by the hand-graded reading.** On 20 questions the system had never seen (gate run 3), the code-checked score was 85% and the release gate held, but the careful-reader score was **20%** (claims fully supported: 32%, against 47% on dev and 57% on held-out). It is a small set and a different grader batch, so do not over-read it; the safe reading is that the dev and held-out hand-graded numbers may be a little optimistic.

## 6. The release gate, and why it changed (D22)

Week 4's original gate was "at least 90% grounded, at most 2% hallucination, three runs in a row", and the standing rule was never to lower it. By the middle of the week the evidence said the 90% was not reachable with a free local model, and Question 18 of the Week 4 spec said what to do then: report honestly, then choose with you between a bigger model, narrowing the promise, or a hosted model. You chose to **split the gate (D22)** and keep the quote real and visible:

- **Release gate (must be zero failures on every run):** no invented or out-of-library citations; no unanswerable question answered. **Met on dev and on held-out look 1.**
- **Display:** the verified quote, time and link come first; the model's sentence second, labelled "AI summary (may say more than the quote)".
- **The 90% and 2% targets stay printed on every scorecard as stretch targets, not met.**

**What was given up, said plainly (the edge cases you accepted):** relevance of a real quote to the question, the meaning of a real quote taken out of context, false premises in new phrasings, refusals of answerable questions, and speed are now reported, not gated.

This was a change to the goalposts after seeing results. It is recorded with that wording so nobody later reads the gate as "90% met".

## 7. False premise: what the data says

A false-premise question assumes something the speaker did not say ("Why does X say Y?" when X said the opposite). We widened the test from 5 questions in one phrasing to 17 in a dozen. Results by content (model-graded, no human check; D24):

| Outcome | Count |
|---|---|
| Refused ("I couldn't find that") | 13 |
| Corrected with a supported quote | 2 |
| Went along with the premise | 1 |
| Other | 1 |

The system rarely agrees with a false premise, but it almost never corrects one. Under the strict status rule (the answer must be labelled "premise corrected") the score is 0 of 17; by content it is 2 of 17. The one answer that went along with the premise is a real failure. E9 tried a separate correction step and made things worse on other questions, so a safe fix needs a more careful design.

## 8. What went wrong (the useful part)

- **Our best number was an overstatement.** For most of the week the headline was 88% on 40 dev questions. It was true under the rules the code can check, and it stood beside a hand-graded figure about 40 points lower. A score from rules that cannot see the failure you care about is not a quality score.
- **Experiments on a small subset produce noise.** Five experiments moved the result by one to four questions of 20. Only a change that moved it by more (the 14B model) was real.
- **Two good-looking fixes cost more than they gave.** E9 fixed three questions and broke three others; E11 doubled the speed and lost two answers.
- **A wrong answer can still look fine in every report.** The two failures that mattered most on dev were questions about episodes not in the library, answered from a related episode. The release gate caught them only after we made "unanswerable questions answered" a gate item.
- **A prompt change breaks "frozen".** E12 changed the prompt after the version was frozen, so the freeze, the tag and the checksum had to be redone. Freezing is a decision that has a price.
- **Tooling gaps.** The sandbox could not run the models, so every run was done on your machine and pasted back. That is slow, and it meant I reported only what you showed me.

## 9. What to take from this as a PM

1. **Measure what the user feels, not what the code can see.** The gap between 79% and 35% was the whole story of the week.
2. **A big model beats a small prompt.** Five prompt experiments on a 7B model did not move the needle; one model change did. Check capacity before wording.
3. **Write the keep rule before the run.** Every decision this week (adopt or revert) was clean because the test was set in advance.
4. **Diagnose before you fix.** Half the early failures were search, not the model.
5. **When the target is out of reach, change the gate in the open.** D22 says what changed, what was accepted, and keeps the original number printed.
6. **Stand-in graders are fine for finding problems and not enough for signing off.** All hand grading this week was by AI readers, and every number carries that label.
7. **Check the whole pipeline when you change one part.** A prompt rule meant for not-in-library questions was tested on all 80 dev questions, because it could have made the system refuse more answerable ones.

## 10. Still open

- **Your own hand grades** on the 30 claims in `evals/grade_sheet_pm_30.csv` (waived, D23, but it is the only thing that would turn "model-graded" into "human-checked").
- **Your own 20 questions** (D20 Q7). The 20 "PM" questions in the 120-question set were written by a model in a PM's voice.
- **Gate run 3 is done** on 20 fresh questions (`data/golden/golden_v2_fresh20.csv`, written by an agent in a PM's voice, not by you): release gate met (0 invented citations, 0 of 3 unanswerable answered), code-checked 85%, hand-graded 20% (section 5).
- **Gate runs 1 and 2 on the frozen version** (dev and held-out) as a three-run record, and held-out looks 2 and 3 (1 of 3 used).
- **The 90% target is not met;** a decision is due before Week 6 on whether to (a) try a hosted model (a policy question outside this project), (b) narrow the promise to the question types that pass, or (c) change what the product claims. The roadmap's Week 6 gate ("still at least 90%") must be re-decided.
- **A real fix for claim support.** E10 failed; the likely lever is what the model is shown and how quotes are chosen, not how claims are worded. A judge that qualifies would also allow the checker idea (E4) to work.
- **False premise:** a correction step that does not over-fire (E9 did).
- **Speed:** 70 to 86 s median against 15 s. Unit selection (E11) halves it at a cost; a smaller or faster model, or a relaxed local target, are the other options.
- **Possible attribution defect:** a name (Dan Shipper) appeared in claims that nothing in the episode supported.
- **Validation step 5 (retrieval on the 120 questions)** still needs to be run on your machine.

## Glossary

| Term | Meaning |
|---|---|
| **Hill-climb** | Improving a system in small measured steps, keeping only what the test says helped |
| **Keep rule** | A pass/fail test for an experiment, written before the run |
| **Diagnosis** | Sorting each failure into a cause (search missed it, model refused, false premise, and so on) |
| **Dev and held-out** | Questions used for tuning, and questions never used for tuning and looked at only three times |
| **Release gate** | The conditions that must hold on every run (here: no invented or out-of-library citations, no unanswerable question answered) |
| **Stretch target** | The original 90% grounded and 2% hallucination goals, still printed, not met |
| **R3 / R4** | Rubric checks that need a reader: does the quote support the claim; is the right person, show and episode named |
| **Judge model** | An AI that grades what code cannot; it did not qualify this week |
| **Blind agent** | A fresh AI reader given only the sheet and the definitions, to avoid bias |
| **Model-graded, no human check** | A result that depends on AI readers only; you waived the human check (D23) |
| **Unit selection** | Showing the model only the best-matching short pieces of transcript instead of all of them |
| **Frozen version** | The exact code, prompt, model and settings used for the gate runs; any change restarts the count |
| **False premise** | A question that assumes something the speaker did not say |
