# Labelling instructions (second labeller)

Thank you for doing this. You will label 20 questions about 16 podcast episodes, **without seeing the answers**. Your labels are compared with Viram's to check that the questions are clear enough for two people to read the same way. Disagreements are useful: they show which questions are ambiguous.

## What you have
- `labelling_sheet.csv`: 20 questions. Columns: `id`, `question`, `type`, `gold_evidence`, `comment`. Fill in `type` and `gold_evidence`, and use `comment` for anything confusing.
- The 16 episodes below. Eleven are **in the library** and five are **outside it** (the app was told to treat those five as not saved).

**Please do not** look at `golden_v0.csv`, `review_v0.md` or any gold answers, and do not ask Viram about a question while you are labelling. If a question is confusing, write that in `comment`. A confusing question is a finding.

## The 16 episodes
### In the library (11)
- Raj Shamani: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisis | Gita Gopinath | FO585 Raj ](https://www.youtube.com/watch?v=dNIef2fGLQY)
- Raj Shamani: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employees | Sachin Puri | FO589 Raj ](https://www.youtube.com/watch?v=8ol3j7o1U7o)
- Raj Shamani: [Why Your Communication Makes People Ignore You & How To Fix It | Vinh Giang | FO588 Raj Sh](https://www.youtube.com/watch?v=BgeNDG5jD60)
- Lenny's Podcast: [Why every company now needs to think and operate like a lab team | Josh Woodward (Google L](https://www.youtube.com/watch?v=3I6QYkccd3o)
- Lenny's Podcast: [How to close $100K+ enterprise deals, step by step | Jen Abel](https://www.youtube.com/watch?v=YS9In813jJ0)
- Lenny's Podcast: [An 86-minute guide to finding PMF | Rob Snyder (Author, The Power of Pull)](https://www.youtube.com/watch?v=19qrLchbQEc)
- Greg Isenberg: [AI Agents Full Course 59 Minutes (for beginners)](https://www.youtube.com/watch?v=eA9Zf2-qYYM)
- Greg Isenberg: [AI Agents are too good at marketing now](https://www.youtube.com/watch?v=uJuxenfe-NU)
- Greg Isenberg: [I'm Obsessed With Grok Bot. Here's Why](https://www.youtube.com/watch?v=1cWZ7Ekff6E)
- Greg Isenberg: [Stop building AI wrappers. Start building agent harnesses.](https://www.youtube.com/watch?v=st61aKW8P5A)
- Greg Isenberg: [The $1M+ Solo Grok Bot Business (Full Course)](https://www.youtube.com/watch?v=67BmkptgTms)

### Outside the library (5)
- Raj Shamani: [Diet Expert: Weight Loss, Calories, Digestion, Sugar & Belly Fats | Pooja Makhija | FO433 ](https://www.youtube.com/watch?v=xi-zHJL5bnI)
- Lenny's Podcast: [Inside the black box of AI: How AI models actually think | Emmanuel Ameisen (Anthropic)](https://www.youtube.com/watch?v=JHo-aiePjoM)
- Lenny's Podcast: [Meta’s Muse: How we launched the most successful consumer product this year | Mona Saranta](https://www.youtube.com/watch?v=WY0cdD4gNoQ)
- Lenny's Podcast: [Why PMs are suddenly valuable again | Tulsee Doshi (Head of Product, Gemini)](https://www.youtube.com/watch?v=qGf2Yvan4Wg)
- Greg Isenberg: [The 9 Stages of AI Agent Adoption, Explained](https://www.youtube.com/watch?v=nRl-7Yhmbog)

## What to fill in for each question
### 1. `type`: choose exactly one of these six
| type | Use it when |
|---|---|
| `single_fact` | The answer is one fact, stated in one place, in **one library episode** |
| `who_when` | The question asks **who said** something or **when** it was said, and one library episode answers it |
| `synthesis` | A good answer needs **two or more library episodes** (for example "what do different guests say about...") |
| `unanswerable` | The question is on topic, but **no episode answers it** (none of the 16) |
| `false_premise` | The question assumes something a speaker **never said** (for example "Why did X say Y?" when X did not say Y) |
| `not_in_library` | The answer exists, but **only in one of the five outside episodes** |

### 2. `gold_evidence`: where the answer is
Write `video_id@mm:ss` using the 11-character ID from the episode link (the part after `v=`) and the time where the answer **starts**. Examples: `abcdefghijk@12:30` or `abcdefghijk@1:02:03`.
- `single_fact`, `who_when`, `not_in_library`: **one** piece of evidence.
- `synthesis`: **two or more**, separated by a semicolon: `abcdefghijk@12:30; bcdefghijkl@45:10`.
- `unanswerable` and `false_premise`: leave it **blank**.

Being within about 15 seconds of the true time is good enough.

## How long this takes
**Plan for 2 to 4 hours**, not one. Each answer sits somewhere in a 30 to 140 minute episode, and you have to find it, or confirm it is not there. It helps to search the transcript: on YouTube, open the episode, choose "Show transcript" in the description, and use your browser's find (Cmd+F). You can do it across several days. Save the sheet as you go.

## Tips
- Decide `unanswerable`, `false_premise` and `not_in_library` **last**: these need you to be fairly sure the answer is not in the episodes, so search a few different words before concluding.
- If you cannot decide between two types, pick the closer one and say why in `comment`.
- Use your own judgement. There is no trick, and nobody expects you to be right every time.

## Returning it
Send the filled-in `labelling_sheet.csv` back to Viram. He runs `uv run podcast-recall eval kappa --labels-b <your file>`, which reports the agreement and lists any questions you labelled differently.
