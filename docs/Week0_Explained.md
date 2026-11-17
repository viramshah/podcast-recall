# Podcast Recall

*Week 0 explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 16, 2026  |  Updated: Nov 17, 2026 (Week 0 closed)  |  Companion to specs/plan.md and specs/decisions.md

> **How to read this:** No coding knowledge is assumed. Every technical word is explained the first time it appears, and there is a glossary at the end. Each Week 0 step has the same five parts: what it is, why we do it, what we did, how you know it worked, and the lesson for you as a PM.

## 1. What you are building, in plain English

Podcast Recall lets you ask a question like "What did the guest say about pricing enterprise software?" and get an answer that comes only from podcasts in your own YouTube library. Every answer shows the episode, the exact quote, the time in the episode, and a link that opens it at that moment.

The goal behind it is trust. Ordinary AI chat tools sound confident even when they invent things. This product is designed so that it **cannot show you a quote that is not really in the episode**, and so that you can **measure** how often it is right.

### How it works, step by step

1. **Library:** it reads which podcasts you subscribe to and save on YouTube.
2. **Find the audio:** for each episode, it finds the show's public feed (called an RSS feed) that contains the audio file.
3. **Transcribe:** a speech-to-text program on your Mac turns the audio into text with a timestamp on every word.
4. **Index:** the text is cut into small chunks of about a minute and stored so it can be searched quickly, both by keywords and by meaning.
5. **Retrieve:** when you ask a question, the system pulls the handful of chunks most likely to contain the answer.
6. **Answer:** a language model running on your Mac writes the answer using only those chunks, and cites them.
7. **Verify:** a checker confirms each quote really appears in the transcript. Anything that does not verify is dropped.
8. **Show:** the answer appears in a chat page with quote cards, timestamps and links.

Steps 4 to 7 are a pattern called **RAG** (retrieval-augmented generation): look things up first, then let the AI write from what it found. It is the most common way to make AI answers reliable, and it is the core skill this project teaches you.

### Why it costs nothing

Everything runs on your own Mac with free software: a local language model through an app called Ollama, local transcription, and a single-file database. The only outside services are free APIs from Google (YouTube) and Podcast Index.

### Is this an "agent"?

Honestly, not in the strict sense. An **agent** is an AI that decides for itself which tools to use, in what order, in a loop until a goal is met. Podcast Recall is a **fixed pipeline**: the steps always run in the same order. That is a deliberate choice. For a trust-focused product, a predictable pipeline with a verifier is safer and easier to test than a free-roaming agent. You will still learn the building blocks agents use: tools, retrieval, grounding, evaluation and guardrails. Section 5 explains how a pipeline could later become an agent.

## 2. What Week 0 is for

Week 0 builds **no product**. It answers one question: *is every ingredient available and working before we invest six weeks?* Each step is a small test of one risky assumption.

| Risky assumption | Week 0 test that checks it |
|---|---|
| My Mac can run AI models fast enough | Step 0.3 (language models) and 0.4 (transcription) |
| I can read my YouTube library | Step 0.5 (Google Cloud and the YouTube API) |
| I can find the audio for podcasts | Step 0.6 (Podcast Index) and 0.8 (seed list) |
| The user interface will work for me and my testers | Step 0.7 (local chat hello world) |
| The 20 episodes I will test on are usable | Step 0.8 (seed episodes) |

> **PM lesson:** This is called **de-risking**. Before you commit a team, find the one thing that could kill the project and test it cheaply. We found two real problems in Week 0 itself (no Spotify Premium, and the MCP block), which cost minutes to discover now and could have cost weeks later.

## 3. The steps, one by one

### Step 0.1: Repo and "constitution"

**What it is.** A **repo** (repository) is a folder tracked by **git**, a tool that records every change so you can go back in time and work on versions side by side. The **constitution** is a small set of documents that state what you are building and which choices are locked in: mission.md, tech-stack.md and roadmap.md.

**Why we do it.** AI coding agents forget everything between sessions. Written specs are the memory. Changing one line in a spec can steer hundreds of lines of code, so decisions get made in documents before they get made in code. This is called **spec-driven development**.

**What we did.** We created the podcast-recall repo, wrote the plan, the decision log, the three constitution files and the first feature spec (U1, the YouTube connector), and committed them.

**How you know it worked.** `git log` shows your commit, and the files are in the specs folder.

> **PM lesson:** Your highest-value work in an AI-built project is the spec. Three minutes of clear writing saves thirty minutes of rework, because the agent builds what you wrote, not what you meant.

### Step 0.2: Install the tools

**What it is.** Programs the project needs: **Homebrew** (an installer for Mac software), **Python** (the programming language), **uv** (manages Python projects), **ffmpeg** (reads and cuts audio and video files), **yt-dlp** (downloads YouTube audio, used only for the video-only decision), **gh** (GitHub from the terminal) and **Ollama** (runs AI models locally).

**Why we do it.** Each later step depends on one of these. Installing them first means later failures point to the real cause.

**What we did.** We checked what you already had (Homebrew, Python 3.12, uv, git, Ollama and Claude Code) and listed what was missing (gh, ffmpeg, yt-dlp), and you installed those.

**How you know it worked.** Running a tool's name in Terminal prints a path instead of "command not found".

> **PM lesson:** "Works on my machine" is the first thing to verify. Teams lose days to environment problems. A short checklist like this is what an engineer does before starting.

### Step 0.3: Local AI models

**What it is.** A **language model** (LLM) is the AI that writes text. **Ollama** is an app that runs open models on your own computer. We pulled three: qwen2.5:7b-instruct (writes the answers), llama3.1:8b (the judge that grades answers) and nomic-embed-text (turns text into numbers that capture meaning, called **embeddings**, used for search by meaning).

**Why we do it.** Local models cost nothing per question and keep your data on your machine. The "7b" and "8b" mean 7 and 8 billion parameters, which is the size that fits a 16GB Mac. Bigger models would be smarter but would be too slow or would not fit.

**What we did.** You pulled all three and ran ollama list, which showed them. The answer model measured about 21 tokens per second, comfortably above the 10 we need.

**How you know it worked.** Each model replies to a test question, and answers arrive at a usable speed (roughly 10 words per second or more).

> **PM lesson:** **Choose the judge from a different model family than the writer.** A model grading its own family's work tends to be too kind. This is a standard evaluation practice, and it is the kind of detail that separates a careful AI product from a demo.

### Step 0.4: Transcription test

**What it is.** **Whisper** is an open speech-to-text model. **mlx-whisper** is a version tuned for Apple chips. We wrote a short script, transcribe_test.py, that transcribes an audio clip and records the start and end time of every word.

**Why we do it.** Word-level timestamps are what make "jump to 34:12" links possible. We also measured the **real-time factor (RTF)**: seconds of computing per second of audio. If RTF were 1.0, a one-hour episode would take an hour.

**What we did.** A 5-minute clip produced 1,075 timestamped words. The first run showed RTF 0.243, but that included a one-time 32-second model download, so the true figure is lower, about 0.14.

**How you know it worked.** The JSON file has a start and end time for each word and the text matches the audio.

> **PM lesson:** Measure before you promise. "Overnight transcription is fine" is a claim; "one hour of audio takes about 8 to 15 minutes" is a number you can plan around.

### Step 0.5: YouTube access (Google Cloud and OAuth)

**What it is.** An **API** is a doorway that lets one program ask another for data. Google offers the **YouTube Data API**. To use it on your account, you need **OAuth**, the "Sign in with Google" permission flow. You create a project in Google Cloud, turn on the API, describe your app on a consent screen, choose a **scope** (the permission you request) and download a credentials file.

**Why we do it.** We request only the read-only scope. **Least privilege** means asking for the smallest permission that does the job, so a bug or leak cannot change your YouTube account. The credentials file is a secret and stays outside the repo.

**What we did.** You created the project, enabled the API, set the app to Testing mode with yourself as a test user, created a Desktop OAuth client, and ran youtube_hello.py, which printed your subscriptions.

**How you know it worked.** The terminal prints your subscription count and channel names after you approve the consent screen.

> **PM lesson:** Know the limits of your data source early. YouTube does **not** expose watch history or transcripts, so your library is subscriptions, playlists and liked videos. In Testing mode the sign-in also expires about weekly. Discovering this now is why D3 exists in the decision log.

### Step 0.6: Podcast Index

**What it is.** **Podcast Index** is a free, open directory of podcasts. Every podcast publishes an **RSS feed**, a web address listing its episodes and the links to the audio files. Podcast Index lets us look up a show and find that feed.

**Why we do it.** YouTube will not give us audio or transcripts, but a show's own RSS feed has the audio file. It is also publisher-provided and public, which keeps us on the right side of platform rules.

**What we did.** You registered for a free key and secret, stored them in a private file outside the repo, and ran podcastindex_hello.py, which signed a request and printed matching feeds.

**How you know it worked.** The script prints a list of feeds with web addresses.

> **PM lesson:** **Treat secrets like passwords.** Keys live in a locked file, never in the repo, never in chat. Also note the result: searching for "Lenny's Podcast" returned three feeds, only one of which was the right show. Matching shows to episodes needs more than a name, which is exactly what the resolver unit (U2) is for.

### Step 0.7: The front-end "hello world"

**What it is.** A **hello world** is the smallest possible working version of something, built only to prove the plumbing works. We built a one-page local chat (a small web server called FastAPI) that sends your message to the Ollama model and shows the reply. It only listens on your own computer (127.0.0.1).

**Why we do it.** The original plan used MCP here (see section 4). MCP was blocked by Qualtrics policy, so we switched to a local web chat. The test still proves the same thing: a user interface can reach the model.

**What we did.** You ran chat_hello.py, opened the page in a browser, typed a message and got a reply.

**How you know it worked.** A reply appears in the chat page.

> **PM lesson:** **When a constraint blocks a plan, change the design, not the rules.** We did not look for a back door around the policy. We moved the product's brain into a plain core library that any front end can call, so the choice of front end became cheap to change. That is the architecture lesson of Week 0.

### Step 0.8: Pick 20 seed episodes

**What it is.** A **seed list** is the small, hand-picked set of episodes the whole project starts with: 20 episodes you have actually heard, from 5 to 8 shows. It is a CSV file (a plain table saved as text) with columns for the YouTube link, show, title, date, whether an RSS feed exists, and notes.

**Why we do it.** You can only judge whether an answer is right about episodes you know. These 20 become the base of the **golden set**, the 120 hand-labelled questions that decide whether the product passes. We also deliberately include video-only shows (no feed), and shows with ads (ad-insertion shifts timestamps), to meet those problems early.

**What we did.** You built a 20-episode CSV from 7 shows. The check script found feeds for 15 of the episodes, and the other 5 have no feed (3 of them were kept on purpose as video-only tests for decision D2). We swapped out clip-style and tutorial videos for full-length episodes you had heard, because the plan needs at least 15 episodes with a feed. You landed exactly on 15, so there is no margin.

**How you know it worked.** The CSV has 20 rows, at least 15 marked has_rss = y, and the check script lists a feed for each show.

> **PM lesson:** Evaluation data is the most valuable asset in an AI product. Models and prompts change every month; a good test set does not. You are building it before you build the product, on purpose.

### Step 0.9: Spotify policy (optional now)

**What it is.** Spotify's developer rules limit how its content can be used with AI, and its developer mode needs a Premium account.

**Why we do it.** You have YouTube Premium, not Spotify Premium, so Spotify moved to version 1.1. Reading the policy now would only matter when it comes back.

**What we did.** We recorded this as decision D1 (decided: defer Spotify to version 1.1).

**How you know it worked.** D1 is marked decided in decisions.md.

> **PM lesson:** Platform rules are product requirements. Read the terms of any data source before you design around it.

### Step 0.10: The Week 0 gate

**What it is.** A **gate** is a checklist that must pass before moving on.

**Why we do it.** It stops you from starting Week 1 on a shaky base.

**What we did.** We ticked the checklist: models answer, a transcript with timestamps exists, subscriptions list prints, Podcast Index returns feeds, the local chat replies, the seed list has 20 rows, and decisions D1 to D7 are recorded. Week 0 was closed on Nov 17, 2026.

**How you know it worked.** Every box is ticked.

> **PM lesson:** Gates are how you stay in control of an AI-built project. You do not read all the code; you decide what must be true before the next stage starts.

## 4. MCP: what it is, and what happened to it

### The idea in one sentence

**MCP (Model Context Protocol)** is an open standard that lets an AI app such as Claude plug into outside tools and data in a uniform way, like a USB-C port for AI.

### Why it exists

Before MCP, connecting an AI app to a calendar, a database or your own code meant a custom integration each time. With MCP, you build **one server** that exposes your capabilities, and any MCP-aware app (a **client**) can use it.

| Part | What it does |
|---|---|
| Client | The AI app the person uses, for example Claude Desktop or Claude Code. |
| Server | A small program you write that offers capabilities. It can run on your own computer. |
| Tools | Actions the AI can call, such as search_episodes or ask. Each has a name, a description and a defined input and output. |
| Resources | Data the AI can read, such as a file or a record. |
| Prompts | Reusable instruction templates the user can pick. |
| Transport | How client and server talk. "stdio" means the client launches the server on the same machine; remote servers talk over the web. |

### How it would have worked here

The original design: Podcast Recall as an MCP server with six tools (sync_library, search_episodes, ask, get_transcript, save_finding, export_findings). You would type a question into Claude Desktop, Claude would decide to call the ask tool, our server would do the retrieval and verification, and Claude would show the result.

### What went wrong, and what we did

When we tried to register the server, Claude Code answered "not allowed by enterprise policy". Qualtrics controls which MCP servers can be added. That is a reasonable security rule, because an MCP server runs code with access to your files and accounts. We treated it as a real constraint and did not work around it.

Decision D7: keep the same six functions in a plain **core library**, and put a **local web chat** and a **command-line tool** on top. MCP becomes an optional thin wrapper for later, only if policy allows.

> **Why this matters for learning MCP:** The skill is not the protocol; it is **designing tools well**. A good tool has a clear name, a precise description, a strict input and output format, and does one job. We kept exactly that discipline in the core functions, so wrapping them in MCP later is a few dozen lines. You can learn MCP properly on a personal machine or an approved setup, using this same core.

### MCP versus the plain web chat

|   | MCP server | Local web chat (our choice) |
|---|---|---|
| Who decides what to call | The AI client (Claude) chooses tools | Our code always runs the same pipeline |
| Needs a Claude client | Yes | No, only a browser |
| Blocked by policy here | Yes | No |
| Who writes the answer | Claude (cloud model) | Local Ollama model |
| Testing and evaluation | Harder, the AI picks the steps | Easier, the steps are fixed |
| Best for | Letting an AI assistant use your tools | A controlled, measurable product |

## 5. Agent-building ideas you are already practising

| Concept | Where it shows up in Podcast Recall |
|---|---|
| Tool | A function with a clear contract, for example ask(question) returns an answer and citations. |
| RAG (retrieve, then generate) | Search the transcripts first; the model may only use what was found. |
| Grounding | Every claim must be backed by a quote from an episode in your library. |
| Guardrail | The verifier drops any citation whose quote is not in the transcript, so a made-up quote never reaches you. |
| Abstention | If nothing relevant is found, the right answer is "I couldn't find that in your podcasts", not a guess. |
| Evaluation (evals) | A golden set plus a rubric measures accuracy, so improvements are numbers, not feelings. |
| LLM-as-judge | A second model grades answers; we check it against human grades before trusting it. |
| Observability | Each answer logs what was retrieved, which model ran and how long it took, so failures can be traced. |

### How a pipeline becomes an agent

To turn this into an agent, you would let the model decide its own steps: search, read a transcript, notice it needs a second search, then answer. The core functions already work as the tools for that. The trade-off is less predictability and harder testing, so the sensible order is **make the pipeline pass its evals first**, then experiment with an agent loop and compare scores.

> **PM lesson:** Do not choose "agent" because it sounds modern. Choose the simplest design that meets the quality bar, and let measured results justify added autonomy.

## 6. The decisions made or pending

| ID | Question | Plain-English status |
|---|---|---|
| D1 | Spotify in version 1? | **Decided.** Defer Spotify to version 1.1. Version 1 is YouTube-only. |
| D2 | Shows with no RSS feed | **Interim.** Videos with no feed are "not indexable" for now. Revisit in Week 1 after reading YouTube's terms and Qualtrics' rules. |
| D3 | Google app status | **Decided.** Testing mode. Testers sign in again about weekly. |
| D4 | Track what you have heard? | **Interim.** Ignore "heard" status in version 1. Revisit after Week 3. |
| D5 | Grading thresholds | Open. A Week 2 decision: quote match 0.90, timestamp within 15 seconds, "partly supported" counts as a fail. |
| D6 | Second person to label questions | Open. Name a second labeller before Week 2. |
| D7 | Front end | **Decided.** Local web chat plus command line; MCP deferred because of policy. |
| D8 | How testers reach the app | Open. Needs an IT answer on exposing a service, plus login. Never expose without login. |

## 7. Where you stand now

| Step | What | Status |
|---|---|---|
| 0.1 | Repo, plan, constitution files, first spec | Done (committed and pushed) |
| 0.2 | Install tools | Done |
| 0.3 | Local models | Done. Answer model about 21 tokens per second |
| 0.4 | Transcription test | Passed (about 1,075 words, timestamps correct at the start) |
| 0.5 | YouTube API | Passed |
| 0.6 | Podcast Index | Passed |
| 0.7 | Local chat hello world | Passed |
| 0.8 | 20 seed episodes | Done: 20 episodes, 15 with a feed (exactly at the gate) |
| 0.9 | Spotify policy | Optional; D1 is decided |
| 0.10 | Week 0 gate | Closed Nov 17, 2026 |

### What comes next

- **Close the small open items:** measure the judge model speed and confirm the video URLs that still carry a "confirm URL" note.
- **Week 2 decisions:** D5 (grading thresholds) and D6 (second labeller). D8 (tester access) can wait until Week 4.
- **Week 1:** build the YouTube connector (U1), match episodes to RSS feeds (U2) and transcribe them (U3). Each unit follows the same loop: write the spec, ask the agent to list ambiguities, let it build, review the diff, verify against the checklist.
- **Week 2** is evaluation first: the rubric and the first 60 golden questions, before any answering code exists.

## 8. Glossary

| Term | Plain meaning |
|---|---|
| API | A doorway that lets one program request data or actions from another. |
| OAuth | The "Sign in with Google" permission system. You approve exactly what an app may access. |
| Scope | The specific permission an app asks for, for example read-only YouTube access. |
| RSS feed | A web address listing a podcast's episodes and audio file links. |
| Transcription | Turning speech into text. Word-level timestamps mean each word has a time. |
| LLM | Large language model: the AI that writes text. |
| Ollama | An app that runs open language models on your own computer. |
| Embedding | A list of numbers that captures the meaning of text, so similar meanings can be found. |
| Chunk | A short slice of a transcript, about one minute, stored for search. |
| RAG | Retrieval-augmented generation: look up relevant text first, then answer from it. |
| Grounded | Every statement is backed by a source the user can check. |
| Hallucination | When an AI states something that is made up or unsupported. |
| Verifier | A check that confirms each quote really appears in the transcript. |
| Golden set | A hand-labelled list of questions and correct answers used to test the product. |
| Rubric | The written rules for grading an answer pass or fail. |
| Eval | A repeatable test run that produces a score. |
| MCP | Model Context Protocol: an open standard for plugging tools and data into AI apps. |
| Client / server | The app a person uses, and the program that provides capabilities to it. |
| Tool (in MCP) | An action an AI can call, with a name and a strict input and output format. |
| Agent | An AI that chooses its own steps and tools in a loop to reach a goal. |
| Pipeline | A fixed sequence of steps that always runs in the same order. |
| Repo / git | A project folder with full change history; git is the tool that tracks it. |
| Spec | A written description of what to build and what done looks like. |
| De-risking | Cheaply testing the riskiest assumption before committing time. |
| Least privilege | Asking for the smallest permission that does the job. |
| Hello world | The smallest working example, built to prove the plumbing. |
