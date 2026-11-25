# Week 4: Hill-climb (retrieval, judge, answer quality, speed), Requirements (v2, 2026-11-22)

Branch: `feature/week4-hillclimb` (from `main` after Week 3 was merged and pushed). Depends on Week 3 (answers, verifier, `eval answer`), Week 2 (rubric, checkers, golden set, harness) and U4 (retrieval). Roadmap gate: **at least 90% grounded and at most 2% hallucination, three consecutive runs.**

Status: **v2. All 20 questions at the end are decided (every recommendation applied, 2026-11-22; decision D20).**

## Where we start (Week 3 baseline, dev split, 40 questions)
- 68% grounded on the deterministic rules only (R1, R2, R5, R7); R3, R4, R6 not yet built, so the real number is lower.
- Zero R1/R2 failures and zero critical failures. The citation safety property holds.
- All 13 failures are R5: refusing answerable questions (10) and false premise (0 of 3).
- Retrieval: recall@5 of 70% on the Week 2 set (target 85%); only 4 passages are shown to the model in the dev runs.
- Median 24 s per answer (target 15 s), 90th percentile 60 s, on a 7B local model.

## What done looks like (the Week 4 gate)
1. **A golden set of 120 questions** (up from 60), with the same split rule (two thirds dev, one third held out) and the same labelling rules, authorship recorded per question.
2. **A judge for R3, R4 and R6** that is calibrated: its agreement with a person on a sample is measured and meets the bar (Q8).
3. **Grounded accuracy of at least 90% and hallucination of at most 2%**, with all five rules running (R1 to R5, R7 reported; R6 tracked), on the runs defined in Q12.
4. **No regression in safety:** zero R1/R2 failures, every run.
5. **Speed recorded** against the latency target, with the decision on the target made (Q14), even if the number is not met.

## The method (diagnose first, then change one thing at a time)
Week 3 showed that a fix can expose the next error. So every change follows the same loop:
```
diagnose (why did each failing question fail?) -> pick the biggest cause -> change ONE thing
 -> rerun dev -> keep or revert on the numbers -> write down what happened
```
- **Dev split only for tuning.** The held-out split is looked at only at planned checkpoints (Q11).
- **One change per experiment, one line in `results.md`** (what, why, before and after, kept or reverted).
- **Cache the model's raw replies** (Q10) so judge and rubric changes can be re-scored without re-answering (a full dev run costs 20 to 30 minutes).

## Workstreams, in order
### A. Diagnosis (no model change; first)
For each dev question that fails, record which of these it is: the right passage was **not retrieved**; it was retrieved but **not shown** (cap or count); it was shown and the **model refused or mis-cited**; or the **gold answer or time is questionable**. `eval answer` stores the retrieved chunk ids per question; a new `eval diagnose` joins them with the golden evidence. Output: a table of causes with counts. This decides where the effort goes.

### B. Retrieval (likely the biggest lever)
Candidates, tried one at a time on dev: the opening-chunk weight (Week 2: 0.5, unconfirmed on held-out); expanding the question with the speaker's likely wording ("free trial" vs "pilot"); a reranker; the per-episode cap and the passage count; chunk size. Measure with `eval retrieval` (recall@5, MRR) and with the end-to-end scorecard.

### C. The judge (R3, R4, R6)
A local model from a **different family** than the answer model (Week 2 decision), given each claim and its quote (R3), the claim and its source labels (R4), and the answer and gold key points (R6), and answering in a fixed JSON shape. Calibrated on a human-labelled sample (Q8, Q9). A person grades by hand if agreement is under 85% (rubric note).

### D. Answer quality
False-premise handling (0 of 3 now); claims that cite real text but do not answer the question (needs the judge to even see it); the choice of answer model. Prompt changes are tried on dev only.

### E. Speed
Fewer or shorter passages, a smaller model, or a changed target. Decided with numbers from the runs, and subject to the accuracy cost (a smaller model refused an answerable question in Week 3).

### F. The 120-question golden set
60 new questions, written and verified against the transcripts the way Week 2 did, balanced across the six types and the shows (no show over about 30%), authorship recorded.

## Out of scope for Week 4
Exports (Week 5); testers and hosted access (Week 6); changing the rubric thresholds (D5 stays unless the data says otherwise and it is logged); hosted AI models (still excluded, tech-stack rule); a larger library, unless Q3 says otherwise.

## Risks
- **The 90% gate may not be reachable with a free local 7B model.** Q18 says what we do if it is not.
- **The judge can be wrong in a correlated way** if it shares a blind spot with the answer model; calibration against a person is the guard.
- **Overfitting to dev.** The held-out checkpoints and a fresh set of PM-written questions (Q12) are the guard.
- **Runs are slow** (about 25 min per 40 questions, over an hour for 120), which limits how many experiments fit.

## Decisions (the 20 questions, all recommendations applied)

### Gate and process
1. **What counts as "grounded" for the 90% gate?** The Week 2 rule: no Critical or Major failure across R1, R2, R3, R4, R5 (R7 reported separately, R6 not gated). **Decided: exactly that.** Hallucination = the share of answers with a Critical failure (R1, R2, R3 unsupported, R4, or R5 invented answer).
2. **How many questions does the gate use?** **Decided: all 120 questions in a final run, plus the held-out 40 reported separately,** so one number cannot hide a held-out collapse.
3. **Grow the library?** **Decided: no.** Keep the 11 library episodes; add questions, not episodes. More episodes means more transcription and a new retrieval baseline. Revisit D4 (full-history upload) after Week 4.
4. **Order of work?** **Decided: A (diagnose) first, then B (retrieval), then C (judge) in parallel with D, then E, with F (new questions) started early** because it needs your review time.
5. **How many experiments before we stop and re-plan?** **Decided: at most 10 logged experiments or two weeks of calendar time, then a checkpoint to decide with you.**
6. **Where do per-question causes get stored?** **Decided: a CSV per run in `evals/scorecards/` (already there) plus a `diagnosis` file; the answers files with quotes stay git-ignored.**

### Golden set and labelling
7. **Who writes the 60 new questions?** **Decided: 20 written by you (the PM) in your own words, 40 drafted by a model from the transcripts and checked by me against the text;** each tagged `pm`, `pm_proxy` or `agent` so results can be cut by author. This closes the "none written by you" gap from Week 2.
8. **Judge calibration bar?** **Decided: at least 85% agreement with a person on 60 claim-level items (the Week 2 rubric figure) and kappa at least 0.6;** below that, R3 and R4 are graded by hand on the gate run.
9. **Who labels the 60 calibration items?** **Decided: you label 30 (about 45 minutes); a cold model reader labels the other 30 and the result is recorded as a stand-in, as in Week 2.** If you can label all 60, better.
10. **Cache raw model replies?** **Decided: yes.** Store the model's raw JSON reply per question and run, so a changed checker or judge re-scores without re-asking the model. Stored privately, not committed.

### Tuning discipline
11. **How often may we look at the held-out split?** **Decided: three times in total** (after the retrieval work, after the judge and answer work, and at the final gate), each logged. Never to choose between two variants.
12. **What are "three consecutive runs"?** Runs at a fixed temperature and seed are nearly identical, so three identical reruns prove little. **Decided: three runs that each differ in what is tested: (1) dev, (2) held-out, (3) a fresh 20 PM-written questions that were never used for tuning;** all must meet 90% and 2%, and the system version is frozen for all three.

### Speed and models
13. **Which answer models do we compare?** **Decided: `qwen2.5:7b-instruct` (current) against `llama3.1:8b`, on dev, same prompt and 4 passages,** plus any other 7 to 9B model that fits 16 GB. The 3B model is dropped (it refused answerable questions).
14. **Latency target?** 15 s is not reachable on this machine with a 7B model (median 24 s warm). **Decided: keep 15 s as the long-term target, set a Week 4 working target of a median under 30 s, and decide the final number after the accuracy work,** because speed that costs accuracy defeats the point.
15. **Which model is the judge?** **Decided: `llama3.1:8b` if the answer model stays Qwen, otherwise a Qwen model;** a different family from the answer model. Its speed (Week 3 measurement) is recorded in the results.
16. **Default passage count?** **Decided: decide with the diagnosis (A);** test 4, 6 and 8 on dev once retrieval is improved, and choose by accuracy first, speed second.

### Answer quality and scope
17. **False-premise path?** The 7B model does not use `premise_corrected` reliably. **Decided: first try two or three worked examples inside the prompt (dev only); if still under 2 of 3, add a separate yes/no check step that runs only when the question contains a claim about what someone said ("Why did X say ...").** The extra call is paid only for those questions.
18. **If 90% is not reached by the checkpoint?** **Decided: report honestly, then choose with you between (a) a larger local model if the machine allows, (b) narrowing the product promise to the question types that pass, or (c) moving the answer model to a hosted one (needs a policy decision outside this project).** Never lower the 90% (standing rule).
19. **Query rewriting by the model?** It could bridge "free trial" and "pilot" but adds a model call per question (slower). **Decided: try keyword expansion from the transcripts first (cheap, no model); add model rewriting only if recall@5 stays under 85%.**
20. **Reranker?** Ollama cannot serve rerankers (D17). **Decided: defer until the diagnosis shows the right passage is retrieved but ranked below the cut;** if it is, try a small local PyTorch cross-encoder, which needs a new dependency and a decision from you first.

## Details added in v2
- **Hallucination, precisely (Q1):** the share of answers with at least one Critical failure: R1 fabricated or misplaced quote, R2 source outside the library, R3 unsupported or contradicted claim, R4 wrong attribution, or R5 an invented answer to an unanswerable question. Refusing an answerable question is a Major failure (it fails grounded accuracy but is not hallucination).
- **Gate numbers (Q2):** one final run over all 120 questions, with the 40 held-out questions reported separately next to it.
- **Authorship tags (Q7):** `pm`, `pm_proxy`, `agent`. Scorecards can be cut by tag. Questions tagged `agent` are verified against the transcripts before use.
- **Experiment log (Q5):** at most 10 logged experiments or two calendar weeks, then a checkpoint with the PM.
- **Held-out looks (Q11):** three in total, each logged in `results.md` with the date and what it was for; never used to choose between variants.
- **Frozen version (Q12):** the code, prompt, models and settings are tagged before the three gate runs and must not change between them.
