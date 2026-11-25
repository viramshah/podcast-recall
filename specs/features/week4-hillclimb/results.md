# Week 4 results (running log)

Status: **in progress.** Method: diagnose, change one thing, rerun dev (or a targeted subset), keep or revert, log here. Held-out looks used: **0 of 3**. Experiments logged: **10 of 10 (budget extended by the PM on 2026-11-25 for E11 to E13; see below)** (E10 reverted) (E9 not adopted) (E1 reverted, E2 not adopted, E3 partial, E4 not adopted, E5a not adopted, E6 provisional, E7 reverted, E8 kept, E9 not adopted).

## Diagnosis of the Week 3 dev run (2026-11-22, 40 questions, 27 pass, 13 fail)
Run `answers_dev_20261122-1949` (identical scores to the earlier run 2: 27/40, so runs are reproducible at temperature 0). `eval diagnose` gives each failure one cause:

| Cause | Count | Questions |
|---|---|---|
| Gold passage not shown to the model (retrieval) | 6 | sf03, sf07, n09, sy07, p11, ww10 |
| Model refused although the gold passage was shown | 4 | sf09, sy01, p13, ww01 |
| False premise not corrected (model said plain `not_found`) | 3 | fp05, p17, p18 |

What this means:
- **Retrieval explains under half (6 of 13).** The model side explains 7 of 13 (4 refusals with the answer in front of it, 3 false premises), so the answer prompt is worth trying first and is cheap to test.
- For the four refusals, the gold passage really was shown (checked for sf09 and ww01: the chunk covers the gold time). The model replied `not_found` after about 16 tokens. At about 3,000 prompt tokens, a 7B model misses an answer sitting in one of four passages.
- For all three false-premise questions the raw reply was a bare `not_found`, never `premise_corrected`: the old rule order made "not found" the easy exit.
- **Prompt size:** 2,400 to 3,200 tokens at 4 passages. Replies that answer are 60 to 160 tokens; refusals 16.
- **Latency varies with the machine more than with the question:** the same answered questions took 19 to 30 s in one run and 70 to 113 s in the next, with identical prompts. Likely power or thermal state or other load. For timing comparisons, plug in, close heavy apps, and repeat.

## Experiments
### E1: rules and worked examples in the answer prompt (2026-11-22) — **REVERTED**
- **Change:** rule 4 said to use `not_found` only when no passage says anything about the question; rule 5 widened `premise_corrected`; three invented worked examples were added (no golden-set content).
- **Run:** 20 questions (7 targets, 13 controls), `answers_dev_20261122-2224`. Grounded 13/20 = 65%, zero R1/R2 failures, zero critical failures, median 45 s.
- **Keep rule:** at least 3 of 7 targets pass, no control regresses. **Not met on both counts.**
  - Targets passing: **2 of 7** (p13, ww01). sf09, sy01 and all three false-premise questions (fp05, p17, p18) still returned a bare `not_found` after about 16 tokens, the same raw reply as before the change.
  - Controls regressed: **2** (sf01 and sf06 went from answered to `not_found`). The unanswerable and not-in-library controls all held (8 of 8).
- **Finding:** wording and examples did not change what the 7B model does on the false-premise questions, so prompt text is the wrong lever for them. They need a structural change (a separate premise check, Q17's fallback) or a different model. The longer prompt (about 3,000 to 3,300 tokens) also cost two answers that were previously right.
- **Action:** `prompting.py` restored to the Week 3 version; the lesson is logged here.

### E2: a different answer model, llama3.1:8b (2026-11-22) — **NOT ADOPTED**
- **Run:** same 20 questions, Week 3 prompt, 4 passages, `answers_dev_20261122-2316`. Grounded 12/20 = 60%, **critical failures 6/20 = 30%**, R1/R2 failures 0, median 83 s (qwen: 45 s on the same machine and set).
- **What it fixed:** all four "model refused with the gold passage shown" questions (sf09, sy01, p13, ww01), and single fact 6/6, who/when 2/2, synthesis 1/1.
- **What it broke:** it answers questions that should be refused. Unanswerable 1/5 (qwen 5/5), not in library 2/3 (qwen 3/3), and 5 controls regressed (n15, p14, p16, un01, nl03). False premise still 0/3 (fp05 was answered, p17 and p18 got a bare `not_found`).
- **Keep rule (more targets, no control regressing, zero R1/R2):** not met. Critical failures of 30% against a gate of 2% are far worse.
- **Finding: the two models sit on opposite sides of the abstention trade-off.** qwen2.5:7b is too cautious (refuses answerable questions); llama3.1:8b is too eager (invents answers to unanswerable ones). Neither can be fixed by choosing a model alone. The decision "answer or say not found" needs its own mechanism that does not depend on how brave the answering model is.
- **Default model stays `qwen2.5:7b-instruct`.** Slower llama speed recorded: median 83 s here.

### E3: decide "answer or not found" from search distance alone (2026-11-22) — **KEEP RULE NOT MET; partial use possible**
- **Run:** `eval abstain --split dev` (no model), `evals/scorecards/abstain_dev.csv`. 32 dev questions should be answered, 8 should say "not found".
- **Best meaning distance by type (min / median / max):** single_fact 0.187 / 0.286 / 0.383; who_when 0.228 / 0.288 / 0.351; synthesis 0.206 / 0.297 / 0.347; false_premise 0.286 / 0.304 / 0.341; **unanswerable 0.258 / 0.293 / 0.339**; **not_in_library 0.391 / 0.402 / 0.434**.
- **Keep rule (at most 1 answerable lost and at most 1 unanswerable answered):** not met. The best single threshold (0.383) loses 0 answerable questions but still answers 5 unanswerable ones (5 errors).
- **What the data says:**
  - **Not-in-library questions are separable**: all three sit above every answerable question (0.391 to 0.434 against a maximum of 0.383). A guard "not found when the best distance is above about 0.385" would catch 3 of the 8 refusals with no answerable loss on dev, and skip the model call for them. The margin is thin (0.383 vs 0.391) and rests on 3 questions, so it is **not adopted yet**; confirm on the held-out split at a planned checkpoint.
  - **Unanswerable questions are not separable.** They are about topics the library does cover (median distance 0.293, in the middle of the answerable range). Whether the fact is actually stated needs reading comprehension, which distance cannot do.
- **Consequence:** the missing mechanism is a check that reads the question and the quote together: "does this quote answer this question?" That is the judge (workstream C, R3-like), used as a production gate. Its use also fits the E2 finding: an eager answerer (llama3.1) plus a more cautious checker (qwen2.5) could balance each other.

### E4: eager answerer plus a cautious checker (2026-11-23) — **KEEP RULE NOT MET; not adopted. But it exposed the real problem.**
- **Change:** a second model (`judge.py`) reads the question and each claim with its quote and returns, per claim, `supported` and `answers_question` (yes/partly/no); a claim stays only if both are "yes" (a premise correction needs only `supported`). Runs after the citation verifier; off unless `--check` / `PODCAST_RECALL_ANSWER_CHECK=1`. Answers by `llama3.1:8b`, checked by `qwen2.5:7b-instruct`.
- **Run:** same 20 questions, passages 4, `answers_dev_20261123-0005`. Grounded 10/20 = 50%, critical failures 1/20, R1/R2 failures 0, median **154 s** (two models: the check alone took 12 to 43 s), R7 0/8.
- **Keep rule:** zero critical (1), all 13 controls pass (5 regressed: p01, p02, p04, sf01, sf06), at least 4 of 7 targets (2: sy01, p13). **Not met.**
- **What the checker did:** of llama's 74 claims it passed 4 and dropped 70: verdicts (supported, answers_question) no/no 52, partly/no 8, yes/no 6, yes/yes 4, partly/yes 1, partly/partly 3. All 8 unanswerable and not-in-library controls stayed "not found" (the checker held that line).
- **Why it dropped so many (checked by rebuilding claims and quotes for p02 and p04):**
  1. **Most of llama's claims were genuinely unsupported by the units it pointed at.** p04 is the clear case: three claims about "bounce rate" point at units whose text is about "10 things small businesses should know". The quote is real transcript text, so the citation verifier (R1, R2) passes it, but it does not say what the claim says. This is the R3 failure the deterministic scorecard cannot see.
  2. **The checker also makes mistakes.** For p02 claim 1, the quote contains "which means they apply to every single project you work in" and qwen still said `supported = no`. A 7B checker is noisy.
- **Important correction to E2:** llama's apparent success on single-fact questions (6/6) came from deterministic rules that cannot judge whether a quote supports its claim. After a support check, only 2 of the 4 refusal targets stay answered. Decisions based only on the R1/R2/R5/R7 scorecard overstate any model that points confidently at the wrong place.
- **What we learned about the design:** with about 3,000 tokens of passage text (4 passages), 7 to 8B models pick the wrong units far too often. That, not the answer wording and not the model brand, is the common cause behind wrong-unit citations, refusals with the answer in view, and slow answers (long prompts).

### E5a: show the model only the 12 best units (2026-11-23) — **KEEP RULE NOT MET; stays opt-in, not the default**
- **Run:** same 20 questions, qwen answers, passages 4, `--unit-top 12`, `answers_dev_20261123-0213`. Grounded 14/20 = 70%, critical failures 0, R1/R2 failures 0, R7 4/8.
- **Prompt:** median **1,663 tokens** (about 3,000 before), units shown 27 of 56 (median). Median time 34 s against 45 s for the earlier qwen run on these same questions (the machine's speed varies between runs, so treat this as indicative).
- **Keep rule (zero critical, zero R1/R2, controls 13 of 13, and either at least 2 of 7 targets or a prompt under 1,500 tokens with no loss):**
  - Zero critical, zero R1/R2, controls 13 of 13: met.
  - Targets passing: **1 of 7** (ww01 newly passes; p13 passed in E1 and E2 but now refuses). Prompt 1,663 tokens, not under 1,500. **The either/or condition is not met.**
- **What it did and did not do:** it cut the prompt by about 45% and some time, and lost nothing, but it did not change the refusals. sf09, sy01 and p13 still return a bare `not_found` with 1,800 to 1,900 tokens in view and the gold chunk shown. So **the refusals are not mainly caused by too much text; qwen2.5:7b is simply quick to refuse.** The false-premise questions behave the same way (3 of 3 plain `not_found`).
- **Differences in pass counts between runs on these 20 questions (13, 14, 12, 10, 13 of 20 across E1 to E5a) are one to four questions, which is within the noise of a 20-question subset.** One question is 5 points here and 2.5 points on the 40-question dev split.
- **Action:** the code and `--unit-top` flag stay (off by default) for later combinations; nothing is switched on. Not adopted.

### E6: demote the opening minutes of each episode (`PODCAST_RECALL_INTRO_WEIGHT=0.5`) (2026-11-23) — **KEPT PROVISIONALLY (candidate default; confirm at held-out look 1)**
- **Change:** only the opening-chunk weight, from 1 to 0.5 (chunks from an episode's first 3 minutes score half). Everything else as the dev baseline: qwen, passages 4, no unit selection, no checker. Full dev split, `answers_dev_20261123-0319`.
- **Result vs the dev baseline (`answers_dev_20261122-1949`, 27/40 = 68%):** grounded **28/40 = 70%**, critical failures 0, R1/R2 failures 0, **R7 10/20 = 50% (was 7/20 = 35%)**, R5 failures 12 (was 13), unanswerable and not-in-library 8 of 8 still correct.
- **What flipped (3 questions):** sf03 and sf07 went from `not_found` to answered and passing (two retrieval fixes); **p04 went from answered to a refusal** (qwen refused with new passages in view). Net +1.
- **Diagnosis after the change (12 failing):** gold passage not shown **4** (n09, sy07, p11, ww10; was 6), model refused with the gold passage shown **5** (p04, sf09, sy01, p13, ww01; was 4), false premise not corrected 3 (fp05, p17, p18).
- **Reading:** the retrieval change does what Week 2 said, now confirmed end to end on dev: two of the six missed questions are fixed and timestamps improve (more answers cite a passage near the gold time). The net gain in grounded accuracy is only +1 question (2.5 points) because the model-side failures, which retrieval cannot touch, dominate (8 of 12), and because a changed prompt moved one answerable question into a refusal (p04). Still within noise on its own; the support comes from R7 +15 points and the Week 2 dev retrieval result (65% to 85%).
- **Decision:** set 0.5 as the working value for the next experiments, **not yet the shipped default.** The held-out check in Week 2 was inconclusive, and held-out is looked at only at planned checkpoints (Q11): look 1 comes after the next retrieval experiment.
- **Prompt:** median 2,939 tokens (all 58 units shown, no selection).

### E7: wide search, narrow prompt (8 passages, 14 best units, intro weight 0.5) (2026-11-23) — **REVERTED (worse)**
- **Run:** full dev split, qwen, `answers_dev_20261123-1647`. Grounded **24/40 = 60%** (E6: 28/40), critical failures 0, R1/R2 failures 0, unanswerable and not-in-library 8 of 8, **R7 7/20 = 35%** (E6: 50%), R5 failures 16 (E6: 12).
- **Speed and size:** median **20.6 s** (best so far; E6 25.2 s), 90th percentile 28.5 s, prompt median 2,185 tokens, units shown 33 of 116 (median).
- **Keep rule (at least 30/40, or not-shown down to 2 or fewer with no more refusals than E6):** not met. Not-shown went 4 to 3 (sf06, n09, ww10) but **refusals went from 5 to 10** and five answerable questions that E6 answered (p01, p03, sf03, sf06, n07) now refuse.
- **Reading:** picking units by their own embeddings fails on short fragments: a 5 to 15 second unit has little context, so the closest units are often not the ones that contain the answer, and with fragments instead of connected text qwen refuses more. Caveat on the diagnosis for this run: "gold passage shown" is judged at chunk level, but the gold unit itself may not have been among the units shown, so the 10 refusals overstate model fault.
- **Action:** the unit selection stays off. E6 (intro weight 0.5, 4 passages, full units) remains the best dev configuration: 28/40 = 70% on the deterministic rules, which can only go down once claim support is scored.

## Checkpoint view after E5a (before E6 and E7)
| Failure cause on dev (13 failing of 40) | Count | What we tried | Outcome |
|---|---|---|---|
| Gold passage never shown (retrieval) | 6 | nothing yet | **untouched: next** |
| Model refuses with the gold passage shown | 4 | E1 prompt, E2 model, E4 checker, E5a smaller prompt | no reliable fix; the 7B model is the limit, or the decision needs a different mechanism |
| False premise not corrected | 3 | E1 prompt examples, E2 model | no fix; needs a structural step (a separate premise check) |

- **All five experiments so far worked on the answer side; retrieval (6 of the 13 failures) has not been touched.** Retrieval changes can be measured in minutes (`eval retrieval`) and, as in Week 2, recall@5 moved from 65% to 85% on dev from the opening-chunk weight alone.
- **Tooling gains that stay:** `eval diagnose`, `--ids`, `--check`, `--unit-top`, `eval abstain`, per-question traces, the prompt-size and units-shown summary.
- **Standing finding:** the deterministic scorecard overstates any model that cites confidently (E4). The judge must score every gate run.

## Held-out looks
None yet (0 of 3).

## Checkpoint after 7 of 10 experiments (2026-11-23)
Best dev configuration: E6 (qwen2.5:7b, 4 passages, opening weight 0.5): 28/40 = 70% on R1, R2, R5, R7 only. Needed for the gate: 36/40 with all rules including claim support. Seven experiments moved the dev score from 68% to 70% and the speed from about 117 s to 25 s (median).

What the evidence says:
1. **Retrieval:** worth keeping (E6) and has about 4 questions left.
2. **Model side (8 of 12 failures):** five experiments (prompt rules and examples, a second 8B model, a checker, a smaller prompt, wide search with a narrow prompt) did not make the 7B model refuse less or correct false premises. This is a capacity or structure limit of the model, not a prompt problem.
3. **Real accuracy is unknown:** the deterministic scorecard cannot see unsupported claims (E4). A calibrated judge is on the critical path for the gate whatever else we do.

Options for the remaining 3 experiments (Q18 checkpoint, decide with the PM): (a) a larger local model that fits 16 GB (for example `qwen2.5:14b-instruct`, about 9 GB) on the same questions; (b) build the judge calibration tooling and label the sample now (needs about 45 minutes of PM time); (c) a separate false-premise check step; (d) narrow the product promise to the question types that pass.

## Judge calibration (workstream C, Q8 and Q9) — tooling built 2026-11-23, labels pending
- **Tooling:** `eval judge-sheet` samples claims from saved runs (hash-ordered, spread evenly across runs) into a sheet with the question, claim and quote and **no judge verdict**; `eval judge-agreement` asks the judge model about the labelled claims the way production does (one call per answer) and reports agreement on "supported", on "answers the question" and on "passes" (both yes), Cohen's kappa on "passes", and how many claims the judge is stricter or more lenient on than a person.
- **Bar (D20, Q8):** agreement on "passes" of at least 85% and kappa at least 0.6, on at least 30 labelled claims. Below that, R3 and R4 are graded by hand on the gate run.
- **Sheet:** `evals/judge_sheet.csv` (git-ignored; it holds transcript quotes): 60 claims, 30 from the qwen E6 run (`20261123-0319`) and 30 from the llama E2 run (`20261122-2316`), so the sample contains both well-supported and poorly supported claims.
- **Labels:** all 60 rows labelled on 2026-11-23 by a fresh AI agent acting as the PM (no access to scorecards or judge output). **These are model-made stand-in labels, not human labels.** Counts: supported yes 20 / partly 21 / no 19; answers question yes 20 / partly 24 / no 16. A pass here shows judge-vs-model agreement only; PM should relabel a subset (15 to 20 disputed rows) before the judge is relied on for the gate.
- **Judge model:** `llama3.1:8b` (a different family from the answer model), settable with `PODCAST_RECALL_JUDGE_MODEL`.

### Full dev run, 14B answerer (2026-11-24) — **88%, just under the 90% gate (deterministic rules only)**
- Config: `qwen2.5:14b-instruct`, intro weight 0.5, 4 passages, no checker, no premise step. Files `evals/scorecards/answers_dev_20261124-0613.*`.
- **35/40 = 88%** (gate 90%; 36 needed). Critical failures 0, R1/R2 failures 0 (the verifier removed 1 claim, R1). R7 timestamp 14/20 = 70%. Synthesis episode coverage 48%.
- By type: single_fact 13/13, synthesis 9/9, unanswerable 5/5, not_in_library 3/3, who_when 5/7, **false_premise 0/3**.
- The 5 failures: fp05, p17, p18 (false premise, bare `not_found`) and p11, ww10 (answerable who/when questions refused).
- Speed: median **148.7 s**, p90 202.1 s (target 15 s; working target 30 s). Answered questions took 110 to 270 s, refusals 45 to 75 s. Prompt median 2,939 tokens.
- **Caveats:** (1) the judge rules are not run, and the judge is not qualified (D21 and calibration notes), so claim support (R3/R4) is unmeasured and 88% is an upper bound. (2) This is the dev split, which the settings were tuned on; held-out has not been looked at (0 of 3).
- E9 (premise step) would turn the 3 false-premise failures into passes but wrongly corrected 3 unanswerable questions on the same run set, so net zero; not adopted.

### Judge agreement result (2026-11-23) — **BAR NOT MET**
- Judge `llama3.1:8b` vs the 60 stand-in labels (model-made, see above): agreement on supported 47%, on answers-the-question 47%, on passes **68%** (bar 85%), kappa **0.19** (bar 0.6). Judge more lenient than the labeller on 18 claims, stricter on 1.
- Pattern: the judge says "supported = yes" for 41 of 60 claims (labeller: 20) and almost never says "partly" (2 of 60, labeller 21), so the three-level scale cannot agree. It is too lenient on support and too strict on answering (37 "no" vs 16).
- Consequence (D20 Q8): R3 and R4 are graded by hand on the gate run until the judge improves. The judge-gate checker (E4) stays off. File: `evals/judge_agreement.csv` (git-ignored).

### Judge agreement, second try: qwen2.5:14b-instruct as judge (2026-11-23) — **BAR NOT MET (closer)**
- Same 60 stand-in labels. Agreement on supported 67%, answers-the-question 50%, passes **80%** (bar 85%), kappa **0.24** (bar 0.6). More lenient than the labeller on 10 claims (was 18), stricter on 2. File: `evals/judge_agreement_14b.csv`.
- Same family as the answering model, so even a pass would have needed an exception.
- **Sample caveat:** the stand-in labeller passes only **5 of 60** claims (supported yes 20 and answers yes 20, but both yes on only 5), so "passes" agreement is mostly both sides failing, and kappa on 5 positives is unstable. The labels are also a single model's judgement. The test cannot certify or condemn the judge on its own; human labels on a larger, more balanced sample are needed.
- Decision: judge still not qualified. R3 and R4 graded by hand on the gate run.

### Strict second labeller (2026-11-23) — model stand-in, 20 disputed rows
- A fresh agent told to be extremely strict re-graded 20 rows (the 10 where the 14B judge was too lenient, the 5 the first labeller passed, 5 others) without seeing any judge output or earlier labels. File `evals/judge_sheet_strict.csv` (git-ignored). Supported: yes 0 / partly 18 / no 2. Answers the question: yes 5 / partly 9 / no 6. **Rows passing both: 0.**
- Main reason: no quote names the speaker, so every claim crediting a named person counts as unattributed; others lean on an inferred referent. Two real failures: fp05#1 (different reason than the quote gives) and sf15#2 (quote only asks the question).
- **Reading:** the strict labeller is too strict to serve as ground truth (zero passes), the first labeller is strict (5 of 60), and the judge is more lenient than both. The disagreement is mostly about one rubric policy question: whether a claim that names the guest, when the question already names them and the quote does not, counts as supported (R3) or as an attribution problem (R4). **Decided 2026-11-23 (D21): option 3, R3 ignores who is named, R4 checks the name against the episode's speaker data.**

### E8: a larger local model, qwen2.5:14b-instruct (2026-11-23) — **KEEP RULE MET (adopt for quality runs; speed decision pending)**
- **Run:** E6 configuration (opening weight 0.5, passages 4, full units, no checker), same 20 questions, `answers_dev_20261123-1747`. Grounded **17/20 = 85%** (qwen2.5:7b on the same 20: 14/20 at best), critical failures 0, R1/R2 failures 0, **R7 6/8 = 75%**, the verifier removed 0 claims.
- **By type:** single_fact 6/6, who_when 2/2, synthesis 1/1, unanswerable 5/5, not_in_library 3/3, **false_premise 0/3**.
- **Keep rule (zero critical, zero R1/R2, all 13 controls pass, at least 4 of the 7 targets):** met. Targets passing: sf09, sy01, p13, ww01 (all four refusals the 7B model made with the answer in view). The three false-premise targets still return a bare `not_found`.
- **Conclusion:** the refusals were a model-capacity limit, not a prompt or retrieval problem: five experiments with the 7B model could not fix them, the 14B model fixed all four on the first try. It also gives the best timestamp accuracy yet (75% of timed questions within 15 s).
- **Speed is the cost.** Median **137 s** (90th percentile 214 s) against a 15 s target and a 30 s working target. Prompt about 3,000 tokens, replies 60 to 160 tokens. Refusals (16 tokens of output) took 80 to 175 s as well, so **almost all the time is the model reading the prompt**, not writing. That makes a smaller prompt the lever: with the 7B model, unit selection (E5a) halved the prompt and cost no accuracy.
- **Not yet known:** claim support (the judge), and how the 14B model does on the other 20 dev questions (a full dev run is needed, about 80 minutes).
- **Decision:** use `qwen2.5:14b-instruct` for the remaining quality experiments; the shipped default stays `qwen2.5:7b-instruct` until the speed decision is made.

### E9: a separate false-premise step (2026-11-23) — **KEEP RULE FAILED (not adopted as is)**
- **Why:** 3 of the 12 dev failures (fp05, p17, p18) are questions of the form "Why does X say ...?" that assume something the speaker did not say. Prompt rules, worked examples and two models never made the answering model use `premise_corrected` (E1, E2, E8).
- **Change:** when the final answer is `not_found` and the question contains an attribution verb (say, tell, recommend, advise, claim, argue, suggest, believe, think and their forms), one more model call with a prompt that does only premise checking. Allowed outcomes: `premise_corrected` (the question itself assumes a person said or advised something and the passages show that person saying something different or the opposite, or discussing the topic without saying what is assumed) or `not_found`. Claims in the reply are pointers like any other and go through the same interpretation and citation verifier, so a correction without a verified citation is dropped and the answer stays `not_found`. Off unless `--premise-step` or `PODCAST_RECALL_PREMISE_STEP=1`. It only runs after a `not_found`, so answered questions never pay for it.
- **Caution recorded before the run:** in the golden set, the pattern "Why does X say/tell ..." matches exactly the five false-premise questions and nothing else (checked across all 60), which is also a sign that the set's false-premise questions share one template. The model-based step does not depend on that wording, but **the result on this set will overstate how well the step generalises to other phrasings.** The 120-question set should add false premises in several phrasings (Q7).
- **Run (planned):** 14B, the same configuration as E8, on 11 questions: fp05, p17, p18 (targets) and n14, n15, p14, p16, un01, nl01, nl03, p20 (the unanswerable and not-in-library controls, which must stay `not_found`).
- **Keep rule:** at least 2 of the 3 false-premise targets pass, all 8 controls stay `not_found`, zero critical failures, zero R1/R2 failures.
- **Result (`answers_dev_20261123-1955`):** 8/11 = 73%. Targets: fp05, p17, p18 all became `premise_corrected` with verified citations (3/3 pass, was 0/3). Controls: only 5 of 8 stayed correct. **Three unanswerable controls (n14, p14, un01) were wrongly turned into `premise_corrected`** (unanswerable 2/5), so 3 R5 failures. Critical failures 0, R1/R2 failures 0, claims removed by the verifier 0. Median 186 s (the extra call adds time on not_found questions).
- **Why it failed:** the verifier checks that a quote is real and in the library, not that it shows the person saying something different. The step found real passages on nearby topics and called that a contradiction. The 14B model cannot tell "the passage contradicts the question" from "the passage is on a related topic". Only a claim-support judge (R3) could separate these, and it is not calibrated yet.
- **Keep rule:** at least 2 of 3 targets (met), all 8 controls stay `not_found` (**failed, 5 of 8**). Net effect on these 11: +3 targets, -3 controls, so zero gain, and the three wrong corrections are confident-looking wrong answers, which is worse than a plain refusal.
- **Decision:** not adopted. Keep the code behind the flag. Possible follow-up (would be experiment 10): require the step to quote the contradicting unit and run the R3 judge on the correction before showing it, but only once the judge passes calibration.


## Hand grading of R3 and R4 (2026-11-24) — sheet built, grades pending
Sheet `evals/grade_sheet_dev_20261124-0613.csv` (git-ignored): all 69 claims from the 27 answered questions of the full 14B dev run. PM grades R3 (yes/partly/no), R4 (yes/no, per D21) and answers-the-question; scored with `eval grade-score`. Rule: any R3 no or R4 no = Critical; R3 partly or a claim that does not answer = Major. Instructions: `evals/grading_instructions.md`.

### Hand grading by a fresh blind agent (2026-11-24) — model stand-in, **far below the gate**
- A fresh agent graded all 69 claims with the R3/R4 definitions and D21 (no knowledge of the gate or the 88%; sheet `evals/grade_sheet_dev_20261124-0613_agent.csv`). Claim level: R3 yes 32 / partly 28 / no 9; R4 yes 67 / no 2; answers the question yes 34 / partly 26 / no 9.
- `eval grade-score`: of 27 answered questions, **2 pass R3+R4 (7%)**, **9 have a Critical failure (33%)**, 16 have a Major failure only. Counting the 8 correct abstentions, grounded accuracy over 40 questions is about **10/40 = 25%** on this reading (the 5 code failures are already among the 30 not counted as passes).
- Drivers: (1) claims that add detail the quote lacks (a timestamp, a definition, a cause, a recommendation); (2) claims that answer only part of a list or timing question; (3) quote cut off mid-sentence; (4) role or name inferred, not stated. Two rows had a name not backed by the episode (R4).
- **Reading:** a stand-in grader, so an estimate, not the gate result; the first labeller and the strict labeller gave similar pictures (few yes). Even so the gap to 90% is too large to be grader noise alone. Rule effect: an answer averages 2.5 claims and "partly" on any one fails it, so 28 of 69 "partly" claims fail most answers. D5 (partly = Major = fail) is provisional and should be revisited with the PM.
- **Decision pending:** see wrap-up.

### E10: claim-writing rules (2026-11-25) — **KEEP RULE FAILED (reverted)**
- **Why:** the blind hand grading found R3 yes on only 32 of 69 claims, mostly claims that add detail the quote lacks, or answer only part of a list or timing question.
- **Change (prompt only, `prompting.py` rules 2 and 3):** a claim restates the cited units in their own words; every fact, number, name, reason or recommendation must be in the cited units; no timestamps, definitions, advice or conclusions of the model's own; hypotheticals and examples not turned into general statements; mid-sentence units claim only what is visible; cite every unit the claim needs; partial answers claim only the part shown.
- **Run (planned):** 14B, E8/full-run configuration, 20 questions: 14 answered ones chosen by id hash, not by result (n06,n07,p01,p03,p07,p08,sf03,sf06,sf09,sf14,sy07,sy13,ww01,ww07, 40 baseline claims) plus 6 controls (n14,n15,p14,un01,nl01,p20).
- **Keep rule (set before the run):** zero R1/R2 failures and zero critical; no more than 1 of the 14 answered questions becomes `not_found`; all 6 controls stay correct; and in a blind hand grading of the new claims, R3 yes rises from 47.5% (19 of 40 claims on the same 14 questions in the 2026-11-24 stand-in grading; R3 no was 12.5%) to at least 65%, with R3 no at most 5%. If it fails, revert `prompting.py` rules 2 and 3 (`git diff` shows the change).
- **Result (`answers_dev_20261125-0527`):** code rules 19/20 = 95%, zero critical, zero R1/R2, controls 6/6, sf06 became `not_found` (13 of 14 answered). Claims 33 (was 40). Blind stand-in grading (`evals/grade_sheet_e10_agent.csv`): R3 yes 16/33 = **48.5%** (baseline 47.5%), R3 no 3/33 = 9% (baseline 12.5%), R4 yes 33/33, answers-the-question yes 19/33. Answers passing R3+R4: 3/13 (baseline on the same 14 questions: 1/14); Critical 3/13 (baseline 5/14); Major only 7 (baseline 8).
- **Keep rule:** R3 yes at least 65% **not met** (48.5%), R3 no at most 5% not met (9%). Reverted `prompting.py`.
- **Reading:** the prompt made claims shorter and cut a few overreaches but did not change how often a claim is fully supported. The remaining gap is mostly "partly": claims that restate a quote that itself covers only part of the question (a "when" question answered with a "what"; advice drawn from an anecdote). That points at what the model is shown (units cut short, the best unit not chosen) more than at claim wording. Small samples (13 answers, 33 claims), stand-in grader.

## Checkpoint after E10 (2026-11-25) and the PM's go-ahead
The PM chose: calibrate with a fresh grader (step 1), then extend the budget for a "what the model is shown" angle (step 2), then bring the product-promise options (step 3). The 10-experiment cap is extended deliberately for **E11 to E13 (3 more)**, each with a keep rule set before the run.

### E11: unit selection with the 14B model, for speed (2026-11-25) — **KEEP RULE NOT MET (speed target met, accuracy cost; stays opt-in)**
- **Why:** time is almost all prompt reading (about 3,000 tokens, 150 s median). E5a halved the prompt on the 7B model at no accuracy cost.
- **Change:** `--unit-top 12` (existing flag), nothing else, on the same 20 questions as E10 (14 answered, 6 controls).
- **Keep rule:** median time at most 90 s; code-rule accuracy no more than 1 question below the same 20 ids in the full 14B dev run `answers_dev_20261124-0613` (the E10 prompt has been reverted, so E11 runs the original prompt); zero R1/R2; all 6 controls correct; the 13 or so answered questions keep at least the baseline hand-graded R3 yes rate (47.5%) on a blind regrade.
- **Result (`answers_dev_20261125-0600`, `--unit-top 12`):** median **74.9 s** (was 148.7 s), p90 93.9 s, prompt median 1,735 tokens (was about 2,940), 26 of 58 units shown. Code rules 18/20 = 90%; critical 0; R1/R2 0 (the verifier removed 1 claim: a unit number that does not exist). Controls 6/6. New refusals: sf03 and ww01 (answerable questions now `not_found`), so the answered count fell to 12. R7 timestamp 3/8 = 38% (was 5/8 to 7/10). Synthesis episode coverage 67%.
- **Keep rule:** median at most 90 s (met); accuracy no more than 1 question below the full run on the same 20 ids (the full run passed all 20 of them; this run 18, **not met**); R3 regrade not run because the accuracy condition already failed.
- **Reading:** unit selection halves the time and costs two answerable questions, as it did (less sharply) with the 7B model. 12 units is too few for some questions. Possible E12: `--unit-top 20` as a middle point.
- **Decision:** not the default; `PODCAST_RECALL_UNIT_TOP` stays opt-in for a fast mode.


### Step 1 calibration: second blind grader on 30 claims (2026-11-25) — the first stand-in grading is stable
- A fresh agent acting as the PM graded a hash-picked 30 of the 69 claims (`evals/grade_sheet_calibration_viram.csv`) without seeing the first grader's labels. Comparison with the first blind grader on the same 30: R3 exact agreement 26/30 (87%), R4 30/30, answers-the-question 26/30 (87%). Never more than one level apart. R3 yes: both 12 of 30, 10 in common. **R3 no (the Critical cases): the same 4 claims by both (30/30 agreement on no vs not-no).**
- **Reading:** two independent model graders agree closely, so the low hand-graded accuracy (R3 yes about 40-47%, about a third of answered questions with a Critical failure) is not one grader's strictness. Still model graders, not the PM: the human check remains the gate evidence.

## D22 applied (2026-11-25): quote-first display and the split gate
- **A (display):** the web page and `ask` now show the verified quote, time and link first and the model's sentence second, labelled "AI summary (may say more than the quote)". The sentence is still inserted as text, never HTML. `tests/test_answers.py` checks the order.
- **B (scorecard):** `eval answer` and `eval run` print a **Release gate (D22)** block (R1/R2 failures, unanswerable questions answered) and keep the D20 targets labelled stretch targets, plus the refusal rate on answerable questions. The latest full 14B dev run passes it (0 R1/R2 failures, 0 of 8 unanswerable or not-in-library questions answered); the E9 premise step would not have (3 unanswerable questions turned into corrections), which is another reason it was not adopted.
- **Not done yet:** the PM's own hand grades on a sample before the held-out look; held-out look 1; the 120-question set with varied false-premise phrasings.

### Task 1 complete: second full grading of all 69 claims (2026-11-25) — model stand-in
- Another fresh agent acting as the PM graded the other 39 claims; with the 30 from the calibration sample this is a full independent second grading (`evals/grade_sheet_pm_stand_in_all69.csv`).
- Against the first blind grader on all 69: R3 exact agreement 64/69 (93%), R4 67/69, answers-the-question 63/69 (91%); **the same claims marked R3 no (69/69 agreement on no vs not-no).**
- Second grader's score (`eval grade-score`): R3 yes 33/69, R4 yes 69/69, answers yes 32/69; answers passing R3+R4 **1/27 (4%)**, Critical **8/27 (30%)**, Major only 18. First grader: 2/27 and 9/27.
- **Reading:** two independent model graders converge (about 30% of answered questions have a Critical R3 failure; almost no whole answer passes the strict rule). This is still not the PM's own grading, which remains the evidence for the gate.

## Configuration frozen (2026-11-25)
- The quality configuration is frozen in `evals/frozen_config.env` (source it in zsh or bash): `qwen2.5:14b-instruct` (E8), opening weight 0.5 (E6), 4 passages (E7 reverted), timeout 600 s (14B answers take up to 270 s), no answer check (E4), no premise step (E9), unit selection off (E5a, E7, E11), the original Week 3 prompt (E1, E10 reverted; `prompting.py` unchanged from `6257d09`), judge not used for gating. A commented fast mode (`PODCAST_RECALL_UNIT_TOP=12`, E11) is marked not for gate runs.
- How to run held-out look 1, the three gate runs and the hand grading, the D22 release gate against the D20 stretch targets, and how to log each run: `specs/features/week4-hillclimb/gate-runbook.md`.
- Any change after the freeze starts the count of gate runs again. Held-out looks used: still 0 of 3. Open with the PM: D20 Q12 defines the three gate runs as dev, held-out and a fresh 20 PM questions, while the runbook runs all questions three times (see the runbook's open points).

### Task 2 complete: the 120-question golden set (2026-11-25) — drafts, PM review pending
- A fresh agent drafted and verified 60 new questions (`data/golden/golden_v1_candidates.csv`): single_fact 14, synthesis 8, who_when 6, false_premise 12 (in 12 different phrasings: "right? what was the number", "isn't it true that", "summarise X's argument for" the opposite, "what made X change his mind", "given that X says", a loaded either/or, a tag question, and so on), unanswerable 10, not_in_library 10; 40 dev, 20 held-out; 20 authored `pm_proxy` (a model imitating a PM, **not** questions a real PM wrote, so the Q7 requirement that 20 come from the PM is still open).
- Merged with v0 into `data/golden/golden_v1.csv`: **120 questions** (80 dev, 40 held-out; false_premise 17, unanswerable 17, not_in_library 15, single_fact 34, synthesis 21, who_when 16). `eval check`: 0 errors, 0 warnings. Gold evidence spot-checked by the agent against the transcripts. Held-out rows follow the v0 convention.
- Open: PM review of the 60 new rows (about 1.5 hours; `eval show <id>` per row), rows flagged uncertain by the agent: v1_032, v1_038, v1_026, v1_012, v1_023, v1_009, v1_059, v1_021. The 17 false-premise questions now give a fairer picture than the original 3 with one phrasing. Held-out rows may not be used for tuning.
