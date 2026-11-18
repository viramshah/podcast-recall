# Podcast Recall

*Unit U3 (ingest and transcribe) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 18, 2026  |  Companion to docs/Week1b_U2_Explained.md, specs/decisions.md (D11, D13, D15, D16) and specs/features/u3-ingest-transcribe/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. It covers what U3 does, **why each decision was made**, what the real data taught us (including the part that went wrong), and what to take from it as a PM.

## 1. What U3 is, in plain English

U2 told the app which podcast episode each of your videos is. U3 gets the **words** of each of those episodes, with the time each sentence was said. Those timestamps are what later let the app say "he said this at 12:30" and link you there.

For each matched episode, U3 does this:

1. **Look for the publisher's transcript.** Many podcasts publish a transcript file next to the audio. If one exists and looks right, use it. It takes seconds and downloads no audio.
2. **Otherwise transcribe the audio yourself.** Download the audio, check it really is audio, and run **Whisper** (an open speech-to-text model that runs on your Mac, so it costs nothing).
3. **Check the result.** Is it empty? Does it end far too early? Are the words-per-minute believable? Is it in the right language? A suspicious transcript is marked `needs_review` and is not used until a human accepts it.
4. **Save a transcript file** in a fixed layout that the next unit (U4, search) will read, delete the audio, and move on.

It never touches episodes that were not matched in U2.

## 2. Where the 16 transcripts came from

| Source | Episodes | Which shows |
|---|---|---|
| Publisher transcript | 12 | All of Lenny's and Greg Isenberg's |
| Whisper, large-v3-turbo model | 4 | All of Raj Shamani's (that feed offers no transcript) |

All 16 ended `ok`, none flagged, and the audio folder ended empty.

## 3. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **D13: publisher first, Whisper as fallback** | Use the publisher's file when it passes the checks | It saves hours of computing, and on the one episode we compared it was 95% similar to Whisper with timings within 2 seconds. It even got names and jargon right where the small Whisper model did not. You decided this before the comparison ran, and the comparison then supported it. |
| **A job queue, one episode at a time** | Each episode is a "job" with a state and up to 3 attempts, with waits of 2 and then 10 minutes between attempts | Transcribing takes long and things fail: a website is down, the Mac sleeps. A queue means a failure on one episode never loses the others. |
| **Crashes and Ctrl+C cost nothing** | A job left half-done goes back in the queue without using an attempt | A stop you chose, or a crash, is not the episode's fault. We tested this for real, and it worked. |
| **Only one worker at a time** | A file lock; a second run is refused with a clear message | Two Whisper runs at once would fight over memory and could write the same file. The OS releases the lock if the program dies. |
| **Safe downloads** | Only http(s) links; no passwords in links; the website must resolve to a public address, checked again at every redirect; size and time limits | A feed is written by someone else, so its links are not trusted. A hostile feed could point "the audio" at `http://127.0.0.1:11434`, which is your own Ollama. The rule keeps the app from being tricked into talking to your own machine or network. |
| **Quality checks that mark, not delete** | A transcript that looks wrong is kept and marked `needs_review` | A human can look and accept it, which is cheaper than redoing the work. A publisher transcript that fails is replaced by Whisper automatically, with the reason recorded. |
| **Language is detected, not assumed** | Whisper detects it, and a mismatch with the feed's language is flagged | Forcing English on a Hindi show would produce confident nonsense. |
| **The transcript file layout is a contract** | A fixed JSON layout with `source`, `timing_detail`, segments and optional words | U4 will read these files. Fixing the layout now means U4 does not have to guess, and a publisher transcript (sentence-sized chunks) and a Whisper one (word-level) look the same to it. |
| **Audio is deleted after success** | `--keep-audio` keeps it | Audio is large. We keep only what we need. |

## 4. What went wrong, and what we learned

This unit had the most surprises, and it is the best example so far of why you test on real data.

- **Whisper small looped on Raj Shamani's show.** The small model (fast, and good on clear English) detected Hindi, wrote garbled text, then repeated "how do you make your food" over and over. In the full run one episode stayed "transcribing" for 45+ minutes. A bigger model, **large-v3-turbo**, transcribed the same audio cleanly, with Hindi words in Latin letters ("bajra jawari", "kachi sabzi"). It is about five times slower, at roughly a quarter of real time.
- **The speed figure was misleading.** The test script reported 1.118 times real time for turbo, but that included a 4-minute model download. Real speed was about 0.24. Always ask what a measurement includes.
- **My own advice was wrong once.** I told you low CPU use meant "stuck". Whisper on this Mac runs on the graphics chip, so low CPU is normal. The duration, not the CPU, was the real signal. I corrected it as soon as the numbers showed it.
- **Ctrl+Z is not Ctrl+C.** A run was paused with Ctrl+Z, which suspends it but keeps its lock, so the next run was refused. The lock worked exactly as designed. It needed a forced kill, and then the crash recovery worked.
- **A real gap in my design.** Nothing stopped a looping episode from holding the queue for an hour. That became **D16**.

## 5. D16: the fix for the gap

- Whisper now runs as a **separate process**, so the app can stop it.
- Each run has a **time limit**: half the audio's length plus 5 minutes, and never under 10.
- If a run hits the limit, or its transcript is flagged, the episode is **retried once with the larger model**. The saved transcript records which model was actually used and why it was retried.
- You choose the retry model with one setting, and can turn it off.

We built it and tested it with simulated timeouts. A real-audio check of it (validation step 15) is optional and takes about an hour.

## 6. What to take from this as a PM

1. **Test on the hardest real case early.** Everything worked on English. The one Hindi/Hinglish show broke the default model. Your instinct to test a Raj Shamani clip first was exactly right.
2. **Fast and cheap versus slow and accurate is a real product choice.** Small is five times faster; turbo is far more robust. The design that uses small by default and escalates to turbo when needed gives most of the speed without the failures. That is a decision about cost and risk, not a technical detail.
3. **Build for failure, not just success.** A queue, retries, crash recovery, a time limit and a lock exist because things fail. The "boring" parts did the work in the real run.
4. **Mark uncertain output instead of hiding or deleting it.** `needs_review` keeps trust: only transcripts that passed the checks (or that you accepted) are used later.
5. **Check what a number includes.** Speed and quality numbers are only useful if you know what was measured.

## 7. Still open

- **Step 15** (real-audio check of D16) is optional. Step 14 (nothing private in git) passed: no audio, transcripts, databases or secrets are tracked, and your Podcast Index key is nowhere in git history.
- **D15** (the quality-check limits) is still provisional: no real transcript was flagged, so we learned nothing about where the limits should sit.
- **D11** (are Hindi/Hinglish episodes in the 90% accuracy test?) now has real evidence: turbo handles them. The decision is still yours.
- Listen to 14:37 to 15:00 of the Diet Expert episode (FO433) to settle the repeated "eat" that appeared in the clip.

## Glossary

| Term | Meaning |
|---|---|
| **Transcript** | The words of an episode, with the time each segment was said |
| **Whisper** | An open speech-to-text model that runs locally. Comes in sizes: small (fast) up to large (slow, accurate) |
| **large-v3-turbo** | A large Whisper model tuned for speed; used here as the stronger option |
| **Job queue** | A list of work with each item's state, so failures and restarts are handled safely |
| **Lock** | A marker that stops two copies of the program from doing the same work at once |
| **Timeout** | A time limit after which a task is stopped |
| **Loop (repetition loop)** | A speech model repeating one phrase over and over instead of the real speech |
| **RTF (real-time factor)** | Seconds of computing per second of audio. 0.05 means an hour of audio takes about 3 minutes |
| **needs_review** | A transcript that failed a check and waits for a human decision |
| **Contract (file layout)** | An agreed file format that two parts of a system rely on |
