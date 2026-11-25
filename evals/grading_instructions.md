# How to grade the R3 / R4 sheet

File: `evals/grade_sheet_dev_20261124-0613.csv` (69 claims from 27 answers; open in Excel or Numbers).
Rows are in random order. If you run short of time, grade the top 35 rows and say so; the score only counts answers whose claims are all graded.

For each row fill three columns (lowercase, exactly these words):

| Column | Question | Allowed |
|---|---|---|
| `r3_supported` | Does the quote say what the claim says? Ignore who is named. | `yes` / `partly` / `no` |
| `r4_attribution` | Are the named person, show and episode right? | `yes` / `no` |
| `answers_question` | If true, does the claim answer what the question asked? | `yes` / `partly` / `no` |

R3 guide: yes = every part of the claim (numbers, causes, recommendations) is in the quote. partly = the gist is there but something is added or stretched. no = the quote does not say it or says something different. Judge only against the quote, not what you know.
R4 guide (decision D21): the quote may not name the speaker. Check the name against what you know of the episode (show and episode columns, the guest). A claim that says "the guest" or "the speaker" is yes. `no` only if a named person is wrong for that episode.
answers_question: a real quote on a related but different topic = no.
`note` is optional (use it for anything odd).

When done, run:
    uv run podcast-recall eval grade-score --answers evals/scorecards/answers_dev_20261124-0613.answers.jsonl --sheet evals/grade_sheet_dev_20261124-0613.csv
