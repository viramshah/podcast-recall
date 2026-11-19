# Labelling instructions (second labeller)

Thank you for doing this. You will label 20 questions about 16 podcast episodes, **without seeing the answers**. Your labels are compared with Viram's to check that the questions are clear enough for two people to read the same way. Disagreements are useful: they show which questions are ambiguous.

## What you have
- `labelling_sheet.csv`: 20 questions. Columns: `id`, `question`, `type`, `gold_evidence`, `comment`. Fill in `type` (**what kind of question it is**, explained below) and `gold_evidence` (where the answer is), and use `comment` for anything confusing.
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

You fill in two columns: first the **kind** of question (the column is called `type`), then **where the answer is** (`gold_evidence`).

### 1. `type`: what kind of question is this?

"Type" does **not** mean how hard the question is, or what topic it is about. It means: **what would a correct answer look like, and where would you find it?** There are six kinds. Find the answer first (search the 16 episodes below), then choose the kind.

**How to decide: ask these in order and stop at the first "yes".**

1. Is the answer found **only** in one of the 5 **outside** episodes, and in none of the 11 library episodes? Then it is **`not_in_library`**.
2. Does the question **assume something that nobody actually said**? For example "Why did X recommend Y?" when X never mentioned Y. Then it is **`false_premise`**.
3. Is the answer **missing from all 16 episodes**, even though the topic is related, and the question does not assume anything false? Then it is **`unanswerable`**.
4. The answer is in the library. Does a good answer need **two or more library episodes**? Then it is **`synthesis`**.
5. Does the question ask **who** said something, or **at what point in the episode** something is said? Then it is **`who_when`**.
6. Otherwise: one fact, stated in one library episode. It is **`single_fact`**.

| type | In plain words | A correct answer looks like |
|---|---|---|
| `single_fact` | One fact, stated in one place | The fact itself |
| `who_when` | Asks who said it, or when in the episode | A speaker and/or a moment |
| `synthesis` | Needs several episodes put together | A comparison or summary across episodes |
| `unanswerable` | Related to the episodes, but they do not say it | "That is not in your library" |
| `false_premise` | Takes for granted something nobody said | A correction: "that was not said" |
| `not_in_library` | The answer exists, but only in an outside episode | "That is not in your library" |

**Invented examples** (these are not from your sheet): "How many ingredients does the host say the sauce needs?" is `single_fact`. "Who first suggests moving the launch to spring, and when?" is `who_when`. "How do the different chefs describe resting dough?" is `synthesis`. "What oven temperature does the host recommend for pies?" is `unanswerable` if pies are never discussed. "Why did the guest say butter is bad for you?" is `false_premise` if the guest never said it. A question whose answer is only in one of the five outside episodes is `not_in_library`.

**When two kinds seem to fit:**
- If the answer is in a library episode **and** in an outside one, it can be answered from the library, so use 4, 5 or 6 above, not `not_in_library`.
- A question that **assumes** something nobody said is `false_premise`, even though the answer is also "not there". `unanswerable` is for questions that do not assume anything false.
- A "when" question that asks about **circumstances** ("when should you...") and not about a **moment in the episode** is not `who_when`. `who_when` is about a point in the episode, or who was speaking.
- If you are still unsure, pick the closer kind and explain in `comment`. That is useful information.

### 2. `gold_evidence`: where the answer is

Write `video_id@mm:ss`: the 11-character ID from the episode link (the part after `v=`), then the time where the answer **starts**. That means where the speaker **begins** giving the answer, not where they finish. For "who said it" questions, use the moment that person starts saying it. Examples: `abcdefghijk@12:30` or `abcdefghijk@1:02:03`.
- `single_fact`, `who_when`, `not_in_library`: **one** piece of evidence.
- `synthesis`: **two or more**, separated by a semicolon: `abcdefghijk@12:30; bcdefghijkl@45:10`.
- `unanswerable` and `false_premise`: leave it **blank**.

Being within about 15 seconds of the true time is good enough. Beware of the **intro teaser**: many episodes open with a short preview of lines from later. If you find a line in the first few minutes, check whether it is repeated later in a real discussion, and use the later one.

## How long this takes
**Plan for 2 to 4 hours**, not one. Each answer sits somewhere in a 30 to 140 minute episode, and you have to find it, or confirm it is not there. It helps to search the transcript: on YouTube, open the episode, choose "Show transcript" in the description, and use your browser's find (Cmd+F). You can do it across several days. Save the sheet as you go.

## Tips
- Decide `unanswerable`, `false_premise` and `not_in_library` **last**: these need you to be fairly sure the answer is not in the episodes, so search a few different words before concluding.
- If you cannot decide between two types, pick the closer one and say why in `comment`.
- Use your own judgement. There is no trick, and nobody expects you to be right every time.

## Returning it
Send the filled-in `labelling_sheet.csv` back to Viram. He runs `uv run podcast-recall eval kappa --labels-b <your file>`, which reports the agreement and lists any questions you labelled differently.
