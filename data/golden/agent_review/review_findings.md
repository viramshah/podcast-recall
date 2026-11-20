# Independent review of golden_v0 (60 questions)

All checks were made against the transcript JSON files. For every question with evidence I read the transcript at the gold time. For every unanswerable, false_premise and not_in_library question I searched all 16 transcripts with several words and phrases.

Verdict key: keep / edit (small fix, listed) / replace (one of the 20 swapped out in new_questions.csv; the new id is shown).

| id | verdict | reason | proposed fix (for edits) |
|---|---|---|---|
| sf01 | keep | Gold matches 10:30 (demand boom, foreign money inflows, government programmes). Natural. | |
| sf02 | keep | Gold correct at 1:10:51 (financial firefighter; confidence in policies). Two-part question but one passage. | |
| sf03 | keep | Matches 1:06:36 (markets, customers, channels, profile of 10 to 20 companies). | |
| sf04 | keep | Matches 1:23:12 to 1:23:34. Speaker says "50% ... don't survive the five-year curve". | |
| sf05 | keep | Self-awareness at 14:39; accurate. | |
| sf06 | keep | Document when emotionally moved, at 1:11:38. Accurate. | |
| sf07 | keep | Gold correct at 6:15 to 6:37. | |
| sf08 | replace (n01) | Question names no guest ("the team", "a Gemini feature"), so it is vague. Gold adds "users" that the speaker does not say. Anecdote is a thin fact. | |
| sf09 | keep | Correct at 25:42 (one in four calls, revisit in a year). | |
| sf10 | keep | Correct at 59:33 to 59:44. | |
| sf11 | keep | Correct at 1:14:51 (accept easy redlines, get legal on a live call). | |
| sf12 | keep | Correct at 8:40. | |
| sf13 | keep | Correct at 25:47 to 25:58 (leaning in vs leaned out). | |
| sf14 | keep | Correct at 6:20. Note that sy08 and sy12 test the same passage; those are the ones replaced. | |
| sf15 | keep | Correct at 41:24 to 41:37; the skill-versus-memory contrast is in the transcript. | |
| sf16 | replace (n02) | Redundant with sy04 (same marketing-is-code passage). The answer ("That work is now handled by...") starts at 5:43, while the topic sentence begins about 5:19, so a 5:46 gold time is shaky. Weak "speaker" wording. | |
| sf17 | keep | Correct at 14:48 to 15:11 (log in on its computer; Tailscale, T3 Code). | |
| sf18 | keep | Correct at 43:13 to 43:24. | |
| sf19 | replace (n03) | "The guest" is never named (it is the Gamma co-founder); a listener cannot tell which episode. Correct content (24:57, 98% prompts, easy and portable) but ambiguous. Could instead be fixed by naming the Gamma guest. | |
| sf20 | replace (n04) | "What does the host say" cannot be checked: the transcript has no speaker labels, and the passage at 5:32 may be the guest (the next line is the host agreeing). Bland topic. | |
| sy01 | edit | Gold time 59:53 is the host restating the point. Rob Snyder starts saying "sell something more service shaped" at about 59:10. Second source (67Bm 44:10) is correct. | gold_evidence: 19qrLchbQEc@59:10; 67BmkptgTms@44:10 |
| sy02 | keep | Both passages correct (47:15 to 47:48; 20:38 to 20:54). | |
| sy03 | keep | Car marketplaces every three hours at 52:16 and eBay GPU listings at 42:54 are accurate. Morning briefing is in the same episode (45:16, 50:58). | |
| sy04 | keep | Both passages correct, including "98% ... dinosaurs" at 35:09. | |
| sy05 | replace (n05) | Three loosely related points (unlearning rate, analyst jobs, study groups) forced under one heading; the Gopinath point is about studying with classmates, not an "ability that matters". Too loose to grade completeness fairly. | |
| sy06 | replace (n06) | Overlaps sf09 (same one-in-four passage). The two guests are answering different things (maturity gap vs case-study fit). | |
| sy07 | keep | Both correct (59:21 to 59:44; 15:07 to 15:19). | |
| sy08 | replace (n07) | Duplicates sf14 and sy12 (agent harness / context). | |
| sy09 | replace (n08) | Weak. 67Bm at 15:08 is a teaser of a walkthrough, not the build advice itself, and the Pluto pivot (1cWZ 5:06) is about reviewing a plan, not building software quickly. The question does not fit the evidence. | |
| sy10 | replace (n09) | Jen Abel at 9:19 is about who to target inside one buyer company, not partner companies. The question stitches two different ideas together. Overlaps sf03. | |
| sy11 | keep | Correct (24:16 to 24:51 design system; 24:58 to 25:24 swipe file). | |
| sy12 | replace (n10) | Third question on the agent harness passage (with sf14 and sy08). | |
| sy13 | keep | Correct (57:07 champion; 46:55 debrief). | |
| ww01 | keep | Agenda approval at 42:53 to 43:04. Within tolerance. | |
| ww02 | replace (n11) | Ambiguous "who": Rob Snyder introduces service-shaped selling at about 59:10; the host only reacts at 59:52. Overlaps sy01. | |
| ww03 | replace (n12) | Same passage as sf10 and sy07. Gold is a bare timestamp. | |
| ww04 | keep | Correct at 43:43 (host, Dan Shipper's frontier team). | |
| ww05 | keep | Soft palate at 43:07. Correct. | |
| ww06 | keep | The cousin story starts at 1:40:01; the silence comes at 1:40:56. Gold time acceptable. | |
| ww07 | keep | Memory difference at 17:56 to 18:12. Correct. | |
| ww08 | replace (n13) | Trivial detail (editor feedback "too yellow") for a who/when question; same region as sf17-type content in the same episode. | |
| ww09 | keep | Loop at 45:47 to 45:58. Correct. | |
| ww10 | keep | Gamma look at 14:57. Correct. | |
| un01 | keep | "pricing page", "price page", "enterprise plan" return nothing in all 16 episodes. | |
| un02 | keep | "SOC 2", "security review", "compliance" absent for Rob Snyder. The only hits are unrelated (Grok Bot episode). | |
| un03 | replace (n14) | Claim fails. Dr Gopinath's episode does mention stablecoins: at 27:38 the host asks "some new stable coin" and she replies at 27:54 that the dollar stays dominant. The key_points list itself includes "stablecoins". A grader could reasonably accept an answer here. | |
| un04 | keep | "go public", "IPO", "public company", "Nasdaq" absent in the Puri episode. | |
| un05 | replace (n15) | Unnatural ("Kubernetes" for a product-lab interview); no listener would ask. Absence is real. | |
| un06 | keep | "booking", "book guests" absent. Slightly odd (Vinh is the guest), but valid. | |
| un07 | replace (n16) | Weak negative: the Mirage / Tesseract video editing software is named in another library episode (uJux 6:06), so a system that answers from the wrong episode is partly right. The question's "guest in the Grok Bot episode" wording is also unclear. | |
| fp01 | replace (n17) | Gold is wrong or incomplete. Jen Abel does recommend a free two-to-three-day pilot (49:25 to 50:45), which is close to a free trial. The premise is not cleanly false, and the gold mentions only charging and a free month. | |
| fp02 | replace (n18) | Premise is far-fetched ("Google should shut down Labs"); absence is real ("shut down", "sunset" not found) but a listener would not ask it. | |
| fp03 | replace (n19) | Weak premise; Rob says "wasting a lot of your life" (1:20:55) about building the wrong thing, not about calls. Absence is real. | |
| fp04 | edit | Premise is garbled: the IMF is the lender, so "the IMF has defaulted on its loans" is not a natural claim. Gold ("nobody has ever defaulted to the IMF", 1:11:12) is right. | question: "Why does Gita Gopinath say countries regularly default on their IMF loans?" |
| fp05 | keep | Valid; Vinh says to document stories. The answer should also note that he says he avoided sharing stories himself for years (1:26:05). Gold is fine. | |
| nl01 | edit | Absent from the library (no salt, sodium or blood pressure hits). Gold time 18:41 is mid-answer; the sodium and blood-pressure explanation starts at about 17:42. | gold_evidence: xi-zHJL5bnI@17:42 |
| nl02 | keep | "Entity or tool" at 42:48; "anthropomorph" absent elsewhere. Wording "the researcher" is acceptable. | |
| nl03 | edit | Absent from the library (no "Jolly"). The reason (corporate logo breaks the spell) starts at about 26:19; 26:59 is 40 seconds later. | gold_evidence: WY0cdD4gNoQ@26:19 |
| nl04 | keep | Fitzpatrick / Monk skin tone absent from the library. Time 26:41 correct. | |
| nl05 | replace (n20) | Not clean. The library Puri episode (8ol3) discusses agentic commerce, 80% agent traffic and making websites ready for agents (7:36 to 8:46, 54:06), so a system could answer part of "get ready for AI shopping agents" from library episodes legitimately. | |

## Summary

Counts: keep 36, edit 4 (sy01, fp04, nl01, nl03), replace 20.

Most important problems:

1. Invalid negatives. un03 is not truly unanswerable (stablecoins are discussed in dNIef2fGLQY at 27:38 and 27:54). nl05 overlaps with the library Puri episode on agentic commerce. un07 and fp01 are partly answerable (another episode names video editing software; Jen Abel does recommend a free short pilot). The gold for fp01 is wrong.
2. Synthesis redundancy and loose pairings. Three questions (sf14, sy08, sy12) test the same agent-harness passage; sy06 repeats sf09; sy10 and sy09 pair passages that do not answer the same thing. sy05 is loose too. This inflates scores on a topic and makes "completeness" hard to judge.
3. Gold times and unlabeled speakers. sy01 and ww02 point at the host's restatement, not where the guest starts (about 40 seconds late); nl01 and nl03 are mid-answer. sf20 and sf19 depend on speaker identity or an unnamed guest that the transcript cannot confirm. The who_when set is nearly all "when" with a bare timestamp as the gold answer, so nothing checks that the system found the right content.

Other observations: the set leans heavily on the five Greg Isenberg episodes for single_fact and who_when, while Lenny's Podcast episode 3I6 and the Gopinath and Puri episodes have few questions. Intro teasers are not a problem: no gold time falls in a teaser (earliest is 6:15).
