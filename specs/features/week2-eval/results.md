# Week 2: Evaluation First, Results (in progress)

Recorded 2026-11-18. Spec: `validation.md` (v2). Automated: 435 tests pass, lint clean.

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
| 8 | `eval retrieval` baseline | Pending |
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

### Suggested question changes (not yet applied; the PM decides)
`sf06` (name the speaker or topic; change "When does he say" to "In what situations"), `sf15` and `sf18` (name the show or episode so "the guest" is clear), `sy07` and `sy10` (narrow them, for example `sy10`: "How do the guests suggest finding distribution partners or channels for a product?").
