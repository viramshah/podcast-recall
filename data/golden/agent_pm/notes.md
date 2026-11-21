# PM replacement set (agent_pm)

20 questions, p01 to p20, each replacing one drafted question of the same type and split. None of the 20 ids on labelling_sheet.csv was replaced.

Replaced (new id: old id): p01:n04, p02:sf17, p03:sf18, p04:sf04, p05:r02, p06:sf11, p07:sy11, p08:sy03, p09:r04, p10:r05, p11:r07, p12:ww09, p13:ww05, p14:n16, p15:un02, p16:un04, p17:n19, p18:r08, p19:nl02, p20:r09.

Why: I picked the drafted items that felt least like something a listener would ask (trivia such as the TPU Harvester award, the $200 plan credit amount, or generic "what do the guests say about X" synthesis prompts) and swapped in topics no existing question covers: NotebookLM origin story, global vs project skills, retention milestone, bounce rate, LinkedIn acceptance benchmarks, founder-led exec outreach, choosing a niche, humans in the loop, demo on the first call, agent security, Linear vs Jira, Vinh's guitar and cards lesson, plus new absent/false-premise/outside-library items.

Counts: single_fact 6, synthesis 4, who_when 3, unanswerable 3, false_premise 2, not_in_library 2. Four are tagged raj (p04, p13, p16, p17).

Verification:
- Every gold time was checked by reading the transcript text at that time (not the first-minutes teasers; p19's 60-20-20 teaser at 0:42 was skipped for the real discussion at 33:26).
- Absences (p14 to p18) were checked with case-insensitive regex search over all 16 transcripts, allowing spaces or hyphens between words and singular/plural stems (e.g. langchain / lang chain, memoriz / memoris, commission / quota / compensation / OTE, godaddy / go daddy / wix / squarespace / hostinger, head of sales / sales hire / chief revenue). Terms that did hit somewhere (e.g. "competitor", "VP of sales", "n8n", "zapier", "CRO") were excluded from key_points because they appear in unrelated contexts; the one "commission" hit (st61aKW8P5A, a 5 percent retailer commission) and "bonus" hits do not address the questions.
- not_in_library items: "60-20-20" appears only in qGf2Yvan4Wg and "Golden Gate" only in JHo-aiePjoM; neither is in any library episode.
