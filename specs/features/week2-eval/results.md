# Week 2: Evaluation First, Results (in progress)

Recorded 2026-11-18. Spec: `validation.md` (v2). Automated: 446 tests pass, lint clean.

## Built
Answer format, golden set loader, checkers R1, R2, R5 and R7, oracle and fabricator (six modes), scorecard, kappa, golden-set checks, and the `eval` commands (`run`, `retrieval`, `check`, `show`, `kappa`, `sheet`).

## Golden set v0 (drafted by the assistant, awaiting the PM's review)
- `data/golden/golden_v0.csv`: 60 questions. Type counts match the plan exactly: 20 single-fact, 13 synthesis, 10 who/when, 7 unanswerable, 5 false premise, 5 not-in-library. Split: 40 dev, 20 held out (7, 4, 3, 2, 2, 2 by type). 17 of 60 are tagged `raj` (28%).
- `data/golden/eval_library.csv`: 11 library episodes. `data/golden/held_out_episodes.csv`: the 5 indexed-but-not-in-the-library episodes (D18, question 17).
- `data/golden/review_v0.md`: the review sheet (question, gold answer, transcript text and link at each gold time).
- Every gold time was checked against the transcript text. Five anchors were corrected during drafting (a repeated cold-open line, an answer starting earlier than the phrase). Four unanswerable questions were replaced after a concept search found overlaps (hiring, stage fright, seed round, a note-taking app). The unanswerable and false-premise questions carry concept phrases in `key_points`, and none of those phrases appear together in any indexed chunk (checked offline against the transcript files).

## Not yet done
| # | Step | Status |
|---|---|---|
| 1 | Read the rubric and apply it by hand | Rubric v1.0 written (`rubric.md`, with worked examples). PM to read it and confirm they would grade the same way |
| 2 | Review the 60 drafted questions and write at least 20 of your own | Pending (PM) |
| 3 | `eval check` | **Passed**: 60 questions, 0 errors, 0 warnings |
| 4 | Second labeller labels 20 items | Pending: Jainam (D6 decided 2026-11-18). Sheet and instructions written |
| 5 | `eval kappa` at least 0.7 | Pending |
| 6 | `eval run --oracle` scores 100% on the real golden set | **Passed** (after the oracle fix): 60/60 = 100%, 0 critical, R7 30/30 |
| 7 | `eval run --fabricate ...` fails as expected | Partly: `invented_quote` run by the PM scored 17/60 = 28%, 43 critical (every answerable question fails, the 17 unanswerable-type ones pass). The other five modes are covered by automated tests; the PM can run them |
| 8 | `eval retrieval` baseline | **Recorded** (2026-11-20, on the final golden set): see below |
| 9 | Compare with the 75% probe result | Pending |
| 10 | Held-out items are kept separate | Pending |
| 11 | Git and secrets check | Pending |

## Findings so far
- **`eval check` on the real database: clean.** 60 questions, 0 errors, 0 warnings.
- **The first oracle run scored 92%, not 100%.** Five R1 failures, all caused by the oracle itself: it built quotes by adding segments until it had two sentences, and the AI Agents Full Course transcript has no punctuation, so it ran on for up to 2,390 words (14 minutes). Two more quotes ran slightly past the 15 second window. Fixed: the oracle stays inside the window and under 60 words, and the answer format now caps a quote at 60 words as well as 2 sentences. A regression test uses a transcript without punctuation. The fabricator run behaved correctly (28% accuracy, 72% critical, only the unanswerable-type questions pass).

## Dry run of the second-labeller step (NOT the D6 gate)
On 2026-11-18 the PM asked the assistant to play the second labeller. That cannot satisfy D6: the assistant wrote the questions and the gold answers, so agreement mostly measures its memory of its own work. It was done only to test the path from sheet to kappa, saved separately as `data/golden/labelling_sheet_claude_dryrun.csv`, and the real labeller (Jainam) still has to label the real sheet.
- **Result:** kappa 1.00 on type, same episodes 100%, times within 15 s 88%. Meaningless as an agreement measure for the reason above. The pipeline works (sheet in, `eval kappa` out, exit code 0).
- **Useful findings from the exercise** (questions a cold reader finds unclear):
  - `sf01`, `sf03`, `sf09`, `sf15`, `ww07` say "the guest" or "the presenter" without naming an episode, and `sf06` says "he". They are findable by search but vague. Consider naming the show or the topic.
  - `sf06` ("When does he say you should write down a story...") reads like a who/when question; it asks for the circumstances. Consider rewording ("In what situations should you...").
  - `fp01` and `fp03` could be labelled `unanswerable` as well as `false_premise`, because the premise is simply absent. The type definitions should say that a question that asserts a statement the speaker never made is a false premise.
  - `nl01` and `nl03` differ by 24 s and 50 s on the time: one picks where the answer begins, the other where it concludes. Gold times should mean "where the answer begins".
- **A real defect it exposed:** the gold evidence for `sy10` (Jen Abel) pointed at 0:09, the cold-open teaser, instead of her answer at 9:19. The same trap had caught `sf07` earlier. Fixed in `golden_v0.csv`. `eval check` now warns when evidence is in the first three minutes of an episode longer than six minutes. Audited every other evidence time: none are that early, and the repeated anchor phrases left (`sy04`) are inside one continuous discussion.

## Model labeller run (an independent subagent; NOT the D6 gate)
On 2026-11-20 the PM asked for a "clone of Jainam". A fresh agent was briefed with only the labelling instructions, the 20-question sheet and the transcripts, and told not to read the golden file, the review sheet or the specs (it reported that it did not; this cannot be verified). Its sheet is `data/golden/labelling_sheet_agent.csv`. It is a model from the same family as the assistant that wrote the questions, so it is a useful cold read but not a human second labeller. Jainam still has to label the real sheet before the gate can be met.
- **Type: 20 of 20 agree, kappa 1.00.** Caveat: the instructions it used already contained the tie-break rules that settle the cases the first dry run found ambiguous (`fp01`/`fp03` and `sf06`), so this run cannot show whether those questions are unclear.
- **Episodes agree on 88% and times within 15 s on 62%.** Every single-fact and who/when item (10 of 10) agrees to within 15 seconds, so those gold times are solid.
- **Multi-minute explanations differ by minutes:** `nl01` 109 s, `nl03` 188 s, `sy04` 206 s (the labeller picked where the topic starts, the gold where the point lands). None of these is scored by R7, so the effect is small, but the guidance was unclear and is now fixed in the instructions.
- **Synthesis gold sets are not unique.** `sy07`: the labeller cited three episodes (Jen Abel, the $1M solo episode and Rob Snyder), the gold has two. `sy10`: the labeller chose Rob Snyder and the $1M solo episode; the gold has Sachin Puri and Jen Abel. "Who to approach first" can mean a person, an industry or a distribution channel. Consequence: the `episode coverage` figure can penalise a correct answer that cites other valid episodes. Treat the gold episodes as a minimum set and let the judge decide completeness (R6), or narrow the question.
- **The labeller's own doubts:** the four synthesis questions are broad; `sf06` has an ambiguous "he" and "when"; `sf15` and `sf18` do not say which episode ("the guest"); `fp01` is false-premise while `un01` is unanswerable.
- **Instruction gaps it reported, now fixed:** no rule for how many synthesis entries are enough (now "the two or three clearest"), and no rule for the time of an explanation that spans minutes.

### Question changes (applied 2026-11-20 at the PM's request)
`sf06` (name the speaker or topic; change "When does he say" to "In what situations"), `sf15` and `sf18` (name the show or episode so "the guest" is clear), `sy07` and `sy10` (narrow them, for example `sy10`: "How do the guests suggest finding distribution partners or channels for a product?").

**Applied:** `sf06` now reads "In what situations does Vinh Giang say you should write down a story you might tell later?"; `sf15` and `sf18` now name the course or episode; `sy07` is narrowed to "How do the guests describe charging a customer money up front?" (gold answer and key points updated to match); `sy10` is narrowed to "How do the guests suggest identifying the right buyers or partner companies to approach first?" (gold evidence unchanged). Only these five rows were patched in `golden_v0.csv`. The review sheet and Jainam's `labelling_sheet.csv` were regenerated (the same 20 ids; no gold answers in it). The two dry-run sheets (`labelling_sheet_claude_dryrun.csv`, `labelling_sheet_agent.csv`) were made on the earlier wording and are kept only as a record.

## Second model-labeller run, on the reworded sheet (NOT the D6 gate)
On 2026-11-20 a second fresh agent, with no context and the updated instructions, labelled the reworded 20-question sheet (`data/golden/labelling_sheet_agent2.csv`). Same caveats as the first run: a model, not Jainam.
- **Type: 20 of 20 agree, kappa 1.00.** Two independent cold readers on different wording both agree with the gold types, so the type definitions look clear. (The caveat that the tie-break rules were in its instructions still applies.)
- **Same episodes: 94%.** The one difference is `sy10` (it chose Sachin Puri and Rob Snyder; the gold has Sachin Puri and Jen Abel).
- **Time within 15 s: 100% on the 10 single-fact and who/when items.** The earlier 62% mixed in explanation and synthesis questions whose time is never scored, where answers span minutes (`nl01` 97 s, `nl03` 51 s, `sy01` 37 s, `sy04` up to 258 s, `sy07` 603 s). `eval kappa` now reports time agreement only for the timed types, with the item count, and episode agreement for all.
- **Its doubts:** `un01` and `un04` could be `false_premise` as well as `unanswerable` ("how does X say to do Y" when X never discussed Y); `sy04`, `sy07` and `sy10` are broad (for `sy07`, "up front" could mean a pilot fee or a project deposit); `ww04` ("who") is ambiguous because the host attributes the idea to someone else; the instructions did not say how to write times past one hour (`h:mm:ss`).

## Independent review of the golden set (a fresh agent, 2026-11-20; applied after rebalancing, see below)
A fresh agent with no project context reviewed all 60 questions against the transcripts and wrote 20 replacements (`data/golden/agent_review/review_findings.md` and `new_questions.csv`). Verdicts: **36 keep, 4 edit, 20 replace.** The assistant verified its main claims.
- **Confirmed:** `un03` is not clean. Gita Gopinath's episode mentions "some new stable coin" at 27:45 (two words, so the assistant's literal search for "stablecoin" missed it). `un07` is not clean: the marketing episode, which is in the library, names a video editing tool ("Mirage Tesseract", 6:06 and 37:37). `fp01` had an incomplete gold: Jen Abel prefers a free two-to-three-day pilot (49:34), the opposite of "never offer a free trial". `sy01`'s gold time (59:53) is late; two independent readers put the start at about 59:10 to 59:20. `nl05` overlaps the library Sachin Puri episode on agent traffic (partly related, not a duplicate answer).
- **Other problems it found:** three questions test the same agent-harness passage (`sf14`, `sy08`, `sy12`); `sy06` repeats `sf09`; `sy05`, `sy09` and `sy10` pair passages that do not answer the same thing; several who/when and fact questions name no speaker ("the team", "the host") that the transcript cannot confirm.
- **Its 20 new questions:** pass the real loader; types and splits match the questions they replace; no duplicates; no teaser times. The assistant read the transcript text at every gold time and found the gold answers supported. Spot checks: `n14` (central banks buying gold) is clean, since even the word "gold" never appears in Gita's episode; `n19` is real (Vinh says at 10:21 that he does not believe accents are a problem). One to watch: `n15` (Rob Snyder and venture capital): Rob mentions "a VC floodgate" at 33:10, which does not answer the question but is borderline.
- **Caveat:** these 20 are model-written (author `agent_reviewer`), not written by the PM from memory. D18 asked for at least a third by the PM, so that requirement is still open.
- **Candidate:** `data/golden/agent_review/golden_v0_candidate.csv` applies the 20 replacements and the four edits (`sy01` time, `fp04` wording, `nl01` and `nl03` times). The current `golden_v0.csv` is unchanged. Before applying: run `eval check` on the candidate against the database; regenerate the review sheet and Jainam's labelling sheet (the replacements change which questions are in the 20: `fp01`, `fp03` and `sy10` are replaced).

### Rebalancing the Raj Shamani share (2026-11-20)
The reviewer's 13 Raj Shamani-tagged replacements pushed the candidate to 27 of 60 (45%), against 28% in the original set and 25% of the four-episode seed. Nine of them were swapped, one for one, for new questions about the other shows (`r01` to `r09`, authored by the assistant and verified against the transcripts), keeping each replaced question's type and split. Result: **18 of 60 (30%)**, the same mix (20/13/10/7/5/5) and the same 40/20 dev and held-out split. Kept from the reviewer's set: `n01`, `n04`, `n06`, `n07`, `n09`, `n13` to `n16`, `n18`, `n19` (11 questions). Authors in the candidate: 49 assistant, 11 reviewer, 0 PM. `r02` was reworded to ask for the amount ($8,000 of credits on a $200 plan), because the transcript's wording of the subsidy sentence is garbled. Candidate: `data/golden/agent_review/golden_v0_candidate.csv`, review sheet: `data/golden/agent_review/review_candidate.md`. **Applied to `golden_v0.csv` on 2026-11-20** after the PM ran `eval check` (0 errors, 0 warnings) and the oracle (60 of 60) on the candidate.

### Golden set v0 as applied (2026-11-20)
- `data/golden/golden_v0.csv`: 60 questions: 20 single-fact, 13 synthesis, 10 who/when, 7 unanswerable, 5 false premise, 5 not-in-library; 40 dev and 20 held out; 18 tagged `raj` (30%). Authors: 49 assistant, 11 reviewer agent, **0 PM**.
- Question ids are now mixed: the original `sf`, `ww`, `sy`, `un`, `fp`, `nl` ids, plus `n01` to `n19` (reviewer) and `r01` to `r09` (assistant, rebalancing). Each new row says what it replaced in its `notes` field. The ids are stable from here on.
- The review sheet `review_v0.md` and the second labeller's `labelling_sheet.csv` were regenerated. The new sheet has 20 questions with ids `fp04, n01, n06, n13, n14, n18, nl01, nl03, r01, r03, sf02, sf05, sf09, sf12, sf15, sy01, sy04, un01, ww01, ww06` (7 single-fact, 4 synthesis, 3 who/when, 2 unanswerable, 2 false premise, 2 not-in-library; no gold answers in it). The two model-labeller dry-run sheets and the earlier agent sheets were made on earlier wording and sets and are kept only as a record.
- **Still open:** D6 (Jainam's labels and kappa on this new sheet); at least a third of the questions written by the PM (D18, question 19); the retrieval baseline on the golden set; the PM's own review of the 60.

## D6 gate: a model stand-in for Jainam, on the final sheet (2026-11-20; NOT a human confirmation)
At the PM's request a fresh agent with no project context played "Jainam" on the regenerated 20-question sheet (`data/golden/labelling_sheet_jainam_proxy.csv`). It used the updated instructions and the transcripts, and was told not to read the golden file or any other agent's work. **It is a model, not Jainam.**
- **Question type: 20 of 20 agree, kappa 1.00** (gate 0.7). Third independent cold model reader to agree on every type.
- **Same gold episode(s): 88%.** **Gold time within 15 s on the 10 single-fact and who/when items: 80%** (8 of 10). The two misses are explanations that span minutes: `sf02` (135 s: the IMF's purpose and its lending test are said two minutes apart) and `sf15` (32 s).
- Synthesis and not-in-library times and episode picks differ, as in earlier runs (`n06`, `r03`, `sy04`, `nl01`, `nl03`); none of those times is scored by R7.
- **Its doubts:** the synthesis questions on learning from customers and validating demand overlap (`n06`, `r03`, `sy01`) and a second reader could pick different episodes; `n18` is false-premise or unanswerable; `nl03` says "corporate logo" while the episode is about keeping a character against internal pushback; `sf05`'s first search hit was a preview line.

## Viram stand-in: 20 questions written as a listener would ask them (2026-11-20; NOT the PM)
At the PM's request a fresh agent played "Viram" and wrote 20 questions in a listener's words, replacing 20 existing questions (never one on Jainam's sheet). Output: `data/golden/agent_pm/new_questions_pm.csv` (ids `p01` to `p20`, author `pm_proxy`) and `notes.md`. **It is a model, not the PM**, and it has no real memory of the episodes: it read the transcripts.
- **Checked by the assistant before applying:** structure (real loader, types and splits match what each replaces, no duplicates, no teaser times, none of Jainam's sheet touched); the transcript text at every gold time supports the gold answer (11 read and confirmed in full, the rest plausible and spot-checked); absences re-tested per episode with a spelling-tolerant search (`p14` absent in Jen Abel's episode, `p15`, `p18` absent everywhere, `p16` has no rivals named in Sachin's episode, `p17` absent in Vinh's); not-in-library claims confirmed (`p19` "60-20-20" appears only in the outside Tulsee Doshi episode, `p20` "Golden Gate Claude" only in the outside black-box episode).
- **Corrected by the assistant:** the false-premise gold answers `p17` and `p18` said only "he never says this". They now state what the speaker actually says (Vinh: record yourself, transcribe, ask an AI for your most common mistakes; Rob: look for pull, a buyer's urgent project; hiring appears only as an example).
- **Known soft spots (agent's own notes):** `p07`, `p08`, `p09` are near existing questions; `p10` pairs two different angles on agent security; `p19` is only loosely adjacent to library talk about building ahead of model capability.
- **Applied to `golden_v0.csv`.** Final: 60 questions, mix 20/13/10/7/5/5, 40 dev and 20 held out, 18 tagged `raj` (30%). **Authors: 32 assistant, 8 reviewer agent, 20 `pm_proxy`, 0 the PM himself.** Jainam's sheet is **frozen**: its 20 ids were not touched. Do not regenerate it with `eval sheet`, because the sampling depends on the ids in the set and would now pick different questions.

## Week 2 gate (2026-11-20): MET WITH MODEL STAND-INS, human confirmation outstanding
| Gate item | Status | Who actually did it |
|---|---|---|
| Rubric v1.0 written with worked examples | Done | Assistant; the PM has not yet confirmed he would grade the same way |
| Deterministic checkers R1, R2, R5, R7 with tests | Done (436 tests) | Assistant |
| Golden set v0, 60 questions, correct mix and split | Done | Assistant, reviewer agent and Viram stand-in |
| Oracle scores 100%; fabricator fails the right rules | Done on the PM's database | PM ran the commands |
| `eval check` clean on the golden set | Done on the PM's database (on the candidate before the last 20 were swapped in; **to re-run on the final file**) | PM ran it |
| **Kappa of at least 0.7 on 20 double-labelled items** | **Met: 1.00 on type** (also 1.00 in two earlier runs on earlier sheets) | **Three cold model readers; not Jainam** |
| **At least a third of the questions written by the PM** | **Met in numbers (20 of 60), but by a stand-in** | **A model, not the PM** |
| Retrieval baseline on the golden set | Not run | PM to run `eval retrieval` |

**Honest status:** the gate numbers are met, but the two items that exist to certify *human* judgement were done by models. Three independent cold model readers agreeing on every type is real evidence that the six type definitions read clearly. It is not evidence that a human second labeller would agree, and it does not stand in for the PM's own questions. Recommendation (the PM decides): proceed to Week 3 now, and have the real Jainam label the frozen sheet, and the PM write or replace a handful of questions, before testers join in Week 6 or before any result is quoted outside the project. Until then every report built on this set should say it was validated with model stand-ins.

## Retrieval baseline on the golden set (2026-11-20, run by the PM)
- **Final-file checks:** `eval check` 0 errors and 0 warnings; the oracle scores 60 of 60, 0 critical.
- **`eval retrieval`:** questions with a gold time (single-fact and who/when): 30. **Recall@5 70%** (target 85%), **recall@10 70%**, **MRR 0.57**. Single-fact 70% on 20, who/when 70% on 10. Synthesis episode coverage in the top 5: 78% on 13. **Results from outside the library: 0** (must be 0). Missed (9): `sf03`, `sf06`, `sf07`, `sf12`, `sf13`, `sf14`, `p11`, `r06`, `ww10`.
- **Reading it:** the baseline is in the same range as the 20-question probe (75%) and below the 85% target, as expected before any tuning (the hill-climb is Week 4). **Recall@10 equals recall@5**, so the nine misses are not near misses: the right chunk is outside the top 10 entirely. That argues against a reranker being enough on its own, since a reranker only re-orders candidates already in the list. Library scoping held on every question (0 leaks).
- **Added:** `eval retrieval --diagnose` re-searches each miss 50 deep with no per-episode cap and reports where the right chunk ranks and its meaning distance, so the next step can separate "buried by near-duplicates" from "the search cannot connect this wording to the answer". Not yet run on the PM's database.

### Diagnosis of the nine retrieval misses (2026-11-20, `eval retrieval --diagnose`, run by the PM)
- **Group A, openings crowd out the answer (7 of 9: `sf03`, `sf07`, `sf12`, `sf14`, `p11`, `r06`, `ww10`).** The chunks that beat the right one start in the first minutes of an episode (for example Josh Woodward at 0:00, 1:29 and 3:04 for `sf07`; Rob Snyder at 0:00, 3:21 and 4:57 for `sf12`; Jen Abel at 1:27 for `r06` and `ww10`). Episodes open with a cold-open teaser and a host summary of everything to come, which reads like a table of contents and matches almost any question about the episode. With only 3 chunks allowed per episode, they use up the slots: for `sf07` and `sf12` the right chunk is 4th in a 50-deep search and is cut off by the cap. The right chunk ranks 4 to 22 in a deep search for six of these seven (`sf03` 6th, `sf07` 4th, `sf12` 4th, `sf14` 10th, `p11` 7th, `r06` 22nd); `ww10` is not in the top 50.
- **Group B, a chunk-boundary near miss (`sf06`).** The right chunk ranks 11th; the chunk returned at 1:12:15 starts 36 seconds after the gold time and covers the same passage.
- **Group C, a wording gap (`sf13` rank 43, `ww10` not in the top 50, and partly `r06`).** The question's words do not resemble the transcript's: `ww10` never names the company, and `r06`'s transcript says "state" where the question says "date".
- **What this means:** a reranker could not fix Group A by itself, because the right chunk is not in the top 10. The cheapest fix is to demote opening chunks in the ranking.
- **Built as an experiment, default unchanged:** `eval retrieval --intro-weight W [--intro-seconds S]` multiplies the score of chunks that start in the first 180 seconds of an episode (only in episodes at least four times that long) by W. W = 1 changes nothing. 7 new tests.
- **Tuning discipline:** run the experiment on the dev split only (`--split dev`); look at the held-out split once, at the end, for the chosen value.

### Intro-weight experiment on the dev split (2026-11-20, run by the PM; held-out split not touched)
Dev split, 20 questions with a gold time (single-fact and who/when). Opening chunks are those starting in the first 180 s of an episode at least 12 minutes long.

| Opening weight | Recall@5 | MRR | Missed |
|---|---|---|---|
| 1 (control, no change) | 65% | 0.51 | `sf03`, `sf06`, `sf07`, `sf12`, `sf14`, `p11`, `ww10` |
| 0.5 | **85%** | **0.62** | `sf06`, `sf14`, `ww10` |
| 0.25 | 85% | 0.62 | `sf06`, `sf14`, `ww10` |
| 0.1 | 85% | 0.62 | `sf06`, `sf14`, `ww10` |
| 0 | 85% | 0.62 | `sf06`, `sf14`, `ww10` |

- **Four questions rescued** (`sf03`, `sf07`, `sf12`, `p11`): all four were Group A (an opening crowding out the answer). **A plateau from 0.5 to 0**, so the gain does not depend on the exact value; the mildest tested value that captures it is 0.5. Weights between 0.5 and 1 have not been tried.
- **Still missed:** `sf06` (chunk boundary), `sf14` (its right chunk is not an opening, so demotion cannot help it) and `ww10` (wording gap, Group C).
- **How much to trust it:** 20 timed questions, so each is 5 points and the gain is four questions. The sign and the plateau are convincing; the exact size is not. The held-out split (20 questions, about 10 timed) is the out-of-sample check and is **still unlooked-at for tuning**.
- **Next:** try 0.9, 0.75 and 0.6 on dev to find the mildest weight that keeps the gain (a milder weight does less harm to a real question whose answer is in the first minutes); then choose one value, look at held-out once (control against the chosen value), and only then change the default.

### Finer intro-weight sweep on the dev split (2026-11-20; held-out still untouched)
| Opening weight | Recall@5 | MRR | Missed |
|---|---|---|---|
| 0.9 | 80% | 0.61 | `sf06`, `sf14`, `p11`, `ww10` |
| 0.75 | 80% | 0.61 | `sf06`, `sf14`, `p11`, `ww10` |
| 0.6 | 80% | 0.61 | `sf06`, `sf14`, `p11`, `ww10` |
| 0.5 | 85% | 0.62 | `sf06`, `sf14`, `ww10` |

- Any demotion at all rescues three of the four questions (80%); `p11` needs the weight to reach about 0.5 (the switch is between 0.6 and 0.5). Weights from 0.5 down to 0 are identical, so 0.5 is the mildest tested value on the plateau.
- **Chosen value, fixed before looking at held-out: 0.5** (opening = first 180 s of an episode at least 12 minutes long). **Caveat:** 0.5 sits at the edge of the plateau (one question, `p11`, flips between 0.6 and 0.5), so the dev result is somewhat sensitive to it.
- **Next:** one held-out evaluation, control (weight 1) against 0.5. Only if it holds up does the default in the code change.

### Held-out check of the intro weight (2026-11-20, run once by the PM)
| Held-out split (about 10 timed questions) | Recall@5 | MRR | Missed |
|---|---|---|---|
| Control (weight 1) | 80% | 0.68 | `sf13`, `r06` |
| Weight 0.5 | 80% | 0.70 | `sf13`, `r06` |

- **Not confirmed.** Recall is identical and MRR rises by 0.02. By the rule fixed beforehand (no better, or only one question: the dev gain may be partly luck), **the default stays at 1 (no change) and the weight stays opt-in.**
- **Why this is inconclusive, not a refutation:** the held-out control was already at 80%, and its two misses are wording gaps (Group C), not openings crowding the answer. Held-out contains no question of the kind the demotion fixes, so it could neither confirm nor refute the effect. It shows no harm.
- **Combined, for the record (not a confirmation):** control 21 of 30, weight 0.5 25 of 30; all four rescued questions are on the dev split.
- **Made usable without code changes:** the environment variable `PODCAST_RECALL_INTRO_WEIGHT` (default 1) applies to every search; an explicit argument or `--intro-weight` overrides it. 1 test.
- **Decision deferred to Week 4,** when the golden set grows to 120 questions and has more openings cases. Until then, retrieval stays at the baseline: **recall@5 70% on all 30 timed questions** (dev 65%, held-out 80%), against the 85% target.
