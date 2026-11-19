# Podcast Recall

*Unit U4 (index and retrieval) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 18, 2026  |  Companion to docs/Week1c_U3_Explained.md, specs/decisions.md (D17) and specs/features/u4-index-retrieval/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. It covers what U4 does, **why each decision was made**, what the real data taught us (including the parts where my first explanation was wrong), and what to take from it as a PM.

## 1. What U4 is, in plain English

By now the app has 16 transcripts, which are 206,000 words of text. U4 makes them **searchable**. Given a question, it finds the few passages most likely to contain the answer, and tells you which episode, which show, what time, and gives a YouTube link that opens near that moment.

It does **not** write an answer. Writing the answer from those passages, and checking each quote, is U6. U4 is the "find the right pages" half of the job. A good answer can only be as good as the passages it is given, which is why this unit gets measured so carefully.

## 2. How a search works, step by step

1. **Cut each transcript into chunks.** A chunk is a window of about two minutes of talk, made of whole sentences, and each chunk starts a little before the previous one ended, so nothing important is lost on a boundary. 16 episodes became 724 chunks.
2. **Index each chunk two ways.**
   - **Keywords:** a classic index of the words in each chunk, so exact terms and phrases are found fast.
   - **Meaning:** each chunk is turned into a list of numbers (an **embedding**) that captures what it is about, using the `nomic-embed-text` model running on your Mac through Ollama. Chunks about similar ideas get similar numbers.
3. **Search both and combine.** Your question goes through both. Each gives a ranked list. The two lists are merged by **reciprocal rank fusion**: a chunk that ranks high in either list, or in both, ends up near the top.
4. **Only your library.** Results come only from episodes in the signed-in user's library, and this limit is applied *inside* both searches, so a chunk from outside the library can never even be ranked.
5. **Show the result.** Episode, show, start and end time, the text, a link, and the scores that explain the ranking.

Why two methods? Keyword search is precise but literal. It cannot find "automobile" when the transcript says "car". Meaning search finds ideas but can wander. On the first 10 test questions, keywords alone scored 70% and keywords plus meaning scored 90%. The three questions that meaning search rescued were all ones worded differently from what the speaker said. (We did not re-run keywords alone on all 20.)

## 3. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **Build U4 before the evaluation work** | You chose to start U4 now, with its own small test set | The roadmap put "eval first" in Week 2. Building U4 first gave real data sooner, at the cost of using a test set we wrote ourselves rather than the formal golden set. |
| **Whole sentences only, with overlap** | A chunk never cuts a sentence, and neighbours overlap | A sentence cut in half cannot be quoted correctly later. Overlap means an answer on a boundary is still in one piece somewhere. |
| **Keyword + meaning, merged by rank** | Reciprocal rank fusion, taking the top 30 from each | Merging by rank position avoids comparing two scores that are on different scales. |
| **No reranker yet** | Deferred | A reranker is a second, slower model that re-orders the top results. It adds a large dependency, so we wanted evidence that we need it. We now have that evidence, and the reranker is the main lever for Week 4. |
| **Results come only from your library** | Scope enforced inside the search | This is a core rule of the rubric (R2): an answer may only cite episodes the user actually has. Enforcing it at the very start is safer than filtering afterwards. |
| **At most 3 chunks per episode** | The default cap | So one long episode cannot fill the whole list. Tested: raising it to 5 or 10 did not help and hurt one question. |
| **Meaning search always answers** | It returns the nearest chunks however far away, with a distance number | Deciding "this is too far, say I don't know" belongs to U6. U4 supplies the distance (0 is identical): about 0.30 for relevant chunks and 0.39 to 0.41 for loosely related ones, so roughly 0.35 is a starting guess for that cutoff. |
| **Everything runs locally, nothing is logged** | Only talks to Ollama on your own computer. Logs hold chunk IDs and counts, never transcript text or your questions. | Same privacy principle as before. A test fails if Ollama's address is not on your own machine. |
| **Safe to stop and rerun** | Each episode is replaced in one all-or-nothing step | A Ctrl+C or a crash never leaves half an episode. We tested stopping a build partway. |

## 4. How we measured it, and what went wrong along the way

We wrote 20 test questions with known answers: a question, the video, and the second where the answer starts. A search counts as correct if the right chunk is in the top 5. The share that pass is **recall@5**, and the target was 85%. Here is the honest story, because it is a good lesson in measuring.

- **The first search looked broken, and it was a scope rule.** Your first search returned only one episode. Search is limited to your YouTube library, and your seed episodes (chosen from a list) are not all in that library. The rule was right and my tooling lacked a way to search the seed list, so I added one.
- **My first scores were unfairly low.** I had rounded answer times down to the second. A chunk that began a fraction of a second later was counted as a miss. I fixed the scoring to allow 2 seconds of slack. A good reminder that a bad measurement can look like a bad system.
- **My first explanation was wrong.** I blamed the "3 chunks per episode" rule for a missed question. You ran the experiment, and raising it did not help. When an experiment disagrees with my theory, the experiment wins.
- **Ten questions were too few.** The first 10 scored 90%. Adding 10 more dropped it to 70%. One question moves a score by 5 to 10 points, so a small test set can flatter you.
- **Shorter chunks made it much worse.** 30-second chunks scored 35%, 45-second ones 55%. A short snippet carries too little context for the meaning model, and the questions are about ideas.
- **One result was luck.** At 125 seconds recall hit exactly 85%, but every size around it scored 75%. We did not set the default to the lucky number. The real finding was a plateau from about 100 to 150 seconds, so we chose 120 in the middle.

## 5. Where it ended up

| Measure | Result | Target |
|---|---|---|
| Recall@5 on 20 questions | **75%** | 85% (not met) |
| Raj Shamani episodes (English with Hindi words) | 83% | |
| Best chunk length | about 120 s with 24 s overlap, the middle of a 100 to 150 s plateau | |
| Index | 16 episodes, 724 chunks, built in minutes | |

The Raj Shamani episodes retrieve about as well as the others (83%, on 6 questions), which was a worry for the Hindi-and-English mix.

We are **below the target**, and the spec said exactly what to do about that: one tuning round (done), and the reranker waits for the Week 4 hill-climb, when the 120-question golden set can judge it fairly. The misses fall into two kinds: five where the right chunk is within the top 50 but ranked too low (a reranker can help), and one that search never found.

## 6. What to take from this as a PM

1. **Measure on more than a handful.** Ten questions said 90%, twenty said 70%. Decide your sample size before you celebrate a number.
2. **Test your measuring stick.** Two of our problems were in the test (rounded times, a library rule) and not in the product.
3. **Don't tune to a lucky peak.** When one setting beats its neighbours by a lot, ask whether it is real. We looked at the neighbours and it wasn't.
4. **Write down what is still open.** We did not reach 85%. The honest record says so, says why, and says what comes next, instead of lowering the target.
5. **Defaults are product decisions.** Chunk size, how many results, how many per episode: each shapes what users see, so each was chosen on evidence and recorded with the reason.

## 7. Still open

- **The reranker** (Week 4), and a re-measure of recall@5 on the real golden set.
- **Link precision:** with 2-minute chunks, a search link can open up to about two minutes before the answer. U6 must cite the exact sentence's time inside the chunk, not the chunk's start.
- **Check the 10 newer answer times** (questions 11 to 20), especially the three Raj Shamani ones. A wrong time would make a question a false miss.
- **D11** (Hindi and Hinglish in the 90% test): retrieval works on those episodes, which is more evidence for keeping them. The decision is still yours.

## Glossary

| Term | Meaning |
|---|---|
| **Chunk** | A two-minute window of a transcript, the unit that gets searched |
| **Embedding** | A list of numbers that captures what a piece of text is about |
| **Hybrid search** | Keyword search and meaning search used together |
| **Reciprocal rank fusion** | A way to merge two ranked lists by position, so a high rank in either counts |
| **Recall@5** | The share of questions where the right chunk is in the top 5 results |
| **MRR (mean reciprocal rank)** | A score for how high the right chunk ranks on average (1.0 means always first) |
| **Reranker** | A second model that re-orders the top results more carefully |
| **Meaning distance** | How far a chunk's meaning is from the question's (0 is identical) |
| **Probe set** | A small test set of questions with known answers |
| **Scope** | The set of episodes a search is allowed to look in |
