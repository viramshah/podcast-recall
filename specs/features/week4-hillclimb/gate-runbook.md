# Week 4: Gate runbook (held-out look 1 and the three gate runs)

Frozen: 2026-11-25. Decisions: D19 (answers and verifier), D20 (Week 4 gate, method, held-out rule), D21 (R3 vs R4), D22 (release gate). Evidence: `results.md` (E1 to E11). Configuration file: `evals/frozen_config.env`.

Run every command from the repository root (`cd ~/Claude./podcast-recall` or wherever the repo lives), in zsh or bash, with Ollama running and `qwen2.5:14b-instruct` and `nomic-embed-text` pulled. A run on 120 questions with the 14B model takes about 5 hours (median about 150 s per question, `results.md`); plug the machine in and close heavy apps.

## 1. The frozen configuration

| Setting | Frozen value | Why (results.md) |
|---|---|---|
| Answer model | `PODCAST_RECALL_ANSWER_MODEL=qwen2.5:14b-instruct` | E8: fixed all four refusals the 7B model made with the answer in view; full 14B dev run 35/40 |
| Opening-minutes weight | `PODCAST_RECALL_INTRO_WEIGHT=0.5` | E6: two retrieval misses fixed, R7 35% to 50%; to be confirmed at held-out look 1 |
| Passages | `PODCAST_RECALL_PASSAGES=4` | Setting of every adopted run; E7 (8 passages, narrow prompt) was worse and reverted |
| Model timeout | `PODCAST_RECALL_ANSWER_TIMEOUT_S=600` | 14B answers take 110 to 270 s (E8, full 14B dev run); the 120 s default would cut them off |
| Answer check | off (`PODCAST_RECALL_ANSWER_CHECK=0`) | E4 not adopted; judge failed calibration |
| Premise step | off (`PODCAST_RECALL_PREMISE_STEP=0`) | E9 not adopted: 3 unanswerable questions answered, which also fails D22 |
| Unit selection | off (`PODCAST_RECALL_UNIT_TOP=0`) | E5a, E7, E11: faster but loses answerable questions |
| Answer prompt | the Week 3 prompt plus the E12 rule (`podcast_recall/prompting.py`, sha256 `607953cd...d09f58`) | E1 and E10 reverted, E12 kept |
| Judge model | not used for gating | Judge agreement 68% and 80% against the 85% bar; R3 and R4 graded by hand (D20 Q8, D22) |
| Pinned defaults | `nomic-embed-text`, chunks 120 s with 24 s overlap | D17; pinned so a stray export cannot change the index |
| Golden set | the 120-question set (file name to be fixed when it is built; see the assumption in section 3) | D20 Q2, Q7 |

**The freeze rule.** The frozen version is: `evals/frozen_config.env`, the code at the tagged commit, the answer prompt, the Ollama model files (their IDs from `ollama list`), the search index and the golden set file. **Any change to any of these after freezing starts the count of gate runs again from run 1**, and the change is logged in `results.md` with its reason. "Three consecutive gate runs" means three runs of the same frozen version with no change and no failed run between them. Fast mode (`PODCAST_RECALL_UNIT_TOP=12`, commented out in the env file) is never used for a held-out look or a gate run.

## 2. Pre-conditions before held-out look 1

All of these must be true, and ticked in `results.md`, before look 1:

- [x] **WAIVED by the PM on 2026-11-25 (D23). The PM's own hand grades on a sample.** The PM (a person, not a model stand-in) has graded at least a sample of claims from the full 14B dev run (`evals/grade_sheet_dev_20261124-0613.csv`, instructions in `evals/grading_instructions.md`; the top 35 rows if short of time) and the result is logged next to the two model graders' results (D22: "Before the held-out look, the PM hand-grades a sample of claims").
- [ ] **The 120-question set is built** (D20 Q2, Q7): 60 new questions, 20 written by the PM in their own words, authorship recorded per question (`pm`, `pm_proxy`, `agent`), the same split rule (two thirds dev, one third held out, so 40 held out), false premises in several phrasings, and `eval check` passes on it.
- [ ] **Nothing was tuned on held-out.** No setting, prompt or threshold was chosen by looking at held-out questions or their answers; the held-out looks counter in `results.md` still reads 0 of 3; the new held-out questions have not been run through `eval answer`.
- [ ] **The version is frozen and tagged** (D20 Q12): the working tree is committed and tagged (commands below), and the prompt and model checks below pass.

Freeze checks (run before look 1 and before every gate run):

```bash
git status --short
```

```bash
shasum -a 256 podcast_recall/prompting.py
```
Expected: `0efc86c1c97bbc077d939c907c80d2d252d88ca7cc26e3d647e2e02b5d470191`.

```bash
git diff --stat week4-frozen-v2 -- podcast_recall/prompting.py
```
Expected: no output (the frozen version 2 prompt: Week 3 plus the E12 rule).

```bash
ollama list
```
Copy the IDs of `qwen2.5:14b-instruct` and `nomic-embed-text` into the run log; they must be the same for every gate run.

```bash
source evals/frozen_config.env && env | grep '^PODCAST_RECALL_' | sort
```
Expected: the ten settings in the env file and nothing else that changes answering (`PODCAST_RECALL_HOME` and `PODCAST_RECALL_OLLAMA_URL` may also appear).

```bash
.venv/bin/python -m pytest -q
```

Tag the frozen version (PM's step, once the working tree is committed):

```bash
git tag -a week4-frozen-v2 -m "Week 4 frozen quality configuration v2: Week 3 prompt plus E12 rule (evals/frozen_config.env)"
```

## 3. Commands

Each block is run on its own. They use `( source evals/frozen_config.env && ... )` so the settings apply only inside the brackets and do not stay in the shell; this works in zsh and bash. `eval answer` exits with a non-zero code when any question fails; that is expected and does not mean the run broke.

**Assumption to fix before running:** the 120-question set's file name is not known yet. The blocks below use `data/golden/golden_v1.csv`; replace it if the file is named differently. Without `--golden`, the commands would use the old 60-question `golden_v0.csv`.

### 3a. Held-out look 1 (held-out split only)

```bash
( source evals/frozen_config.env && .venv/bin/podcast-recall eval answer --golden data/golden/golden_v1.csv --split heldout --out evals/scorecards/heldout_look1_20261125.csv )
```

Optional, no extra model calls (cause per failing question):

```bash
.venv/bin/podcast-recall eval diagnose --golden data/golden/golden_v1.csv --answers evals/scorecards/heldout_look1_20261125.answers.jsonl --out evals/scorecards/heldout_look1_20261125.diagnosis.csv
```

Look 1 is a measurement, not a choice: run only the frozen configuration, never a second variant to compare (D20 Q11).

### 3b. The three gate runs (D20 Q12: dev, held-out, fresh PM questions)

D20 Q12 (approved) defines the three runs by what each tests, because three reruns of the same questions at a fixed temperature are nearly identical. All three use the frozen configuration; run the freeze checks in section 2 before each. Change the date in the file names.

Gate run 1, the dev split:

```bash
( source evals/frozen_config.env && .venv/bin/podcast-recall eval answer --golden data/golden/golden_v1.csv --split dev --out evals/scorecards/gate1_dev_YYYYMMDD.csv )
```

Gate run 2, the held-out split (this is held-out look 3; see section 6):

```bash
( source evals/frozen_config.env && .venv/bin/podcast-recall eval answer --golden data/golden/golden_v1.csv --split heldout --out evals/scorecards/gate2_heldout_YYYYMMDD.csv )
```

Gate run 3, the 20 fresh questions never used for tuning (`data/golden/golden_v2_fresh20.csv`, written by an agent in a PM's voice, `eval check` clean; not questions the PM wrote). All 20 are in the file's `dev` split, which here only means "not held-out":

```bash
( source evals/frozen_config.env && .venv/bin/podcast-recall eval answer --golden data/golden/golden_v2_fresh20.csv --split dev --out evals/scorecards/gate3_fresh20_YYYYMMDD.csv )
```

All three must meet the release gate (section 4). The D20 stretch targets (90% and 2%) are reported for each.

### 3c. Hand grading of R3 and R4 (every gate run, and look 1)

The judge is not qualified, so R3 and R4 are graded by a person on each run. Write the sheet (it holds transcript quotes and is git-ignored):

```bash
.venv/bin/podcast-recall eval grade-sheet --golden data/golden/golden_v1.csv --answers evals/scorecards/gate1_all_YYYYMMDD.answers.jsonl --out evals/grade_sheet_gate1_YYYYMMDD.csv
```

Fill in `r3_supported` (yes/partly/no), `r4_attribution` (yes/no) and `answers_question` (yes/partly/no) for every row, following `evals/grading_instructions.md` and D21 (R3 ignores who is named; R4 checks the name against the episode). Then score it:

```bash
.venv/bin/podcast-recall eval grade-score --golden data/golden/golden_v1.csv --answers evals/scorecards/gate1_all_YYYYMMDD.answers.jsonl --sheet evals/grade_sheet_gate1_YYYYMMDD.csv
```

For held-out look 1, use `evals/scorecards/heldout_look1_20261125.answers.jsonl` and `evals/grade_sheet_heldout_look1_20261125.csv` in the same two commands. `grade-score` counts only answers whose claims are all graded, so say in the log if the sheet was only partly graded. Expect about 2.5 claims per answered question (about 250 claims per 120-question run).

Quote-first display check (D22 A), once per frozen version:

```bash
.venv/bin/python -m pytest -q tests/test_answers.py -k quote_time_and_link
```

Then start the web chat with the frozen settings and open the address it prints:

```bash
( source evals/frozen_config.env && .venv/bin/podcast-recall serve )
```

Ask one question and confirm by eye that the quote, time and link come first and the sentence is labelled "AI summary (may say more than the quote)".

## 4. Release gate versus reported metrics

**Release gate (D22). Must hold on every run, including look 1 and all three gate runs. One failure stops the series:**
1. Zero invented or out-of-library citations: the scorecard line "Invented or out-of-library citations (R1, R2)" is `0/n`.
2. No unanswerable or not-in-library question answered: the line "Unanswerable or not-in-library questions answered" is `0/m`.
3. Quote-first display: the test above passes and the page shows the quote before the labelled AI summary.

**Reported on every run, not release conditions:** R3 claim support and R4 attribution (hand-graded, section 3c), the answers-the-question rate, refusals of answerable questions ("Answerable questions refused"), R7 timestamp accuracy, synthesis episode coverage, and time (median and 90th percentile).

**Stretch targets (D20), still printed on every scorecard and currently NOT met:** at least 90% grounded and at most 2% of answers with a Critical failure. Note that the scorecard's "Grounded accuracy" line uses the deterministic rules only (R1, R2, R5, R7); D20 counts an answer as grounded only if it also passes R3 and R4, so the honest number combines the scorecard with the hand grades, and it is lower (the two model graders put it near 25% on dev). Passing the release gate does not mean the 90% target is met, and a report must not say it does.

## 5. How to log each run in results.md

Append (never rewrite) one entry per run under "Held-out looks" (look 1) or a new "Gate runs" section, in this shape:

```markdown
### Gate run N (or Held-out look 1): YYYY-MM-DD
- Version: tag `week4-frozen-v2`, commit <hash>, `evals/frozen_config.env` unchanged, prompt sha256 607953cd..., models qwen2.5:14b-instruct <ollama id>, nomic-embed-text <ollama id>, golden set <file>.
- Command: <the exact block from the runbook>. Files: `evals/scorecards/<name>.csv` (+ .answers.jsonl, .trace.jsonl, git-ignored).
- Release gate (D22): R1/R2 failures x/n; unanswerable answered x/m; quote-first check passed yes/no. **PASS / FAIL.**
- Reported: deterministic grounded x/n; hand-graded answers passing R3+R4 x/y (grader: PM or stand-in, sheet fully or partly graded); Critical x/y; answerable refused x/k; R7 x/t; median s, p90 s.
- Split view: dev x/80, held-out x/40 (and the PM-written questions if they can be cut).
- Stretch targets (D20): 90% grounded met / not met; 2% Critical met / not met.
- Count: gate runs in a row on this version: N of 3 (or: held-out looks used: N of 3).
- Anything odd (timeouts, restarts, machine state).
```

Also update the counters in the status line at the top of `results.md` ("Held-out looks used: N of 3") in the same edit.

## 6. The three held-out looks

| Look | When (D20 Q11) | What it is for | Status |
|---|---|---|---|
| 1 | After the retrieval work | Confirm on held-out what was tuned on dev: the opening-minutes weight 0.5 (E6, unconfirmed on held-out since Week 2), the 14B model's dev result (E8, 35/40), and observe the not-in-library distance margin (E3) without adopting it. Measurement of the frozen version only | Not used |
| 2 | After the judge and answer work | Check the version after any remaining judge or answer-side change (for example E12 or E13 if run, or a change made after the PM's hand grades). If nothing changes between look 1 and the gate runs, this look is not needed and stays unused | Not used |
| 3 | At the final gate | Gate run 2 (the held-out split) on the frozen version, reported separately next to all 120 (D20 Q2) | Not used |

**Held-out looks used: 0 of 3.** A look is never used to choose between two variants. Each look is logged with its date and purpose.

## Open points this runbook does not settle

- **The three gate runs.** Resolved 2026-11-25: section 3b follows D20 Q12 (dev, held-out, fresh PM questions). The earlier draft ran three reruns on all questions; that was removed.
- **How the gate runs count as held-out looks.** Each gate run on all questions includes the held-out split. This runbook treats the three gate runs together as look 3 (one frozen version, no choice made from them). If a gate run fails and the version changes, the restarted series needs a held-out look that may no longer be available; decide with the PM.
