# Podcast Recall

*Week 1 (unit U1, the YouTube connector) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 17, 2026  |  Companion to docs/Week0_Explained.md, specs/plan.md, specs/decisions.md and specs/features/u1-youtube-connector/

> **How to read this:** Like the Week 0 guide, no coding knowledge is assumed and every technical word is explained when it first appears. A glossary of the new terms is at the end. This guide covers what was built, **why each decision was made**, what went wrong along the way, and what you should take from it as a PM.

## 1. What U1 is, in plain English

U1 is the part of Podcast Recall that **knows what is in your YouTube library**. It does four jobs:

1. **Signs in as you**, with permission that can only *read* your YouTube account, never change it.
2. **Reads your library**: the videos you liked, the playlists you made, and the latest episodes of the podcast channels you tell it about.
3. **Stores that list on your Mac** in a small database, and keeps it fresh when you sync again.
4. **Forgets you on request**: one command deletes your sign-in and your saved library, and tells Google to cancel the permission.

It does **not** find audio, transcribe anything or answer questions. Those are U2 (match each YouTube video to its podcast episode), U3 (download and transcribe) and the later units. U1 is the foundation: everything else needs to know *which episodes are in your library*.

You use it from the terminal today, with commands such as `auth`, `sync`, `status`, `channels` and `revoke`. The web chat will call the same underlying functions later (the "core library" idea from decision D7).

## 2. How a sync works, step by step

When you run `sync`, the app does this in order:

1. **Subscriptions:** reads the complete list of channels you subscribe to.
2. **Playlists:** reads the playlists you own and their titles.
3. **Liked videos:** finds your Liked-videos list through your own channel.
4. **Uploads of marked channels:** for each channel you marked as a podcast, finds its list of uploads.
5. **Video IDs:** lists the video IDs in every one of those sources.
6. **Details:** asks YouTube for the title, channel, date and length of any video it has not seen before (or has not refreshed in 30 days).
7. **Apply changes:** adds new videos to your library and removes ones that left a source, one source at a time.
8. **Record the run:** saves how it went, so `status` can tell you.

A video that sits in two sources (say, Liked and a channel) is counted once. It stays in your library as long as at least one source still has it.

## 3. The decisions, and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **D9: what counts as your library** | Everything in playlists you own, plus Liked videos, plus the uploads of channels you mark as podcasts | A YouTube subscription is a *channel*, not a video. Pulling every upload of every channel you follow (you have over 150) would mean thousands of videos, slow syncs, and mostly non-podcast content. You choose which channels are podcasts. |
| **Channel items are cumulative** | Once a podcast episode is in your library, new uploads do not push it out | Otherwise your library would quietly lose old episodes as new ones arrive, and a question about an older episode would stop working. |
| **Safe removal** | An item is removed from a playlist or Liked source only if the app read the *whole* list successfully | If a sync stops halfway, a partly read list looks like "you deleted everything after page 2". The app would then delete real data. A failed read must never delete anything. |
| **D10: share episode data** | Episode details (and later transcripts) are stored once; your library, sign-in and notes are private to you | Transcribing an episode is slow. If two testers have the same episode, doing it twice wastes hours. |
| **D12: where data lives** | One private folder, `~/.podcast-recall/`, outside the code folder | Your library, logs and later audio and transcripts are personal. Keeping them out of the repo means they can never be committed to GitHub by accident. |
| **Identify you by YouTube channel, not email** | The app stores your YouTube channel ID and name | Reading an email address needs an *extra* Google permission. We promised to ask only for read-only YouTube access (the principle of **least privilege**: ask for the smallest permission that does the job). This was found in review, before any code was written. |
| **Never use YouTube search** | Search is banned in the code, and a test fails if anyone adds it | We only need to read *your* lists, and search is a different, quota-limited tool. The ban also stops an accidental, expensive habit. |
| **Deleted and private videos** | They are stored as "unavailable" and skipped, counted, and not asked about again for 30 days | Playlists show placeholders for videos that are gone. Remembering them saves quota on every later sync. Detecting them by "YouTube returned nothing" is more reliable than matching the word "Deleted", which changes by language. |
| **Revoke** | Deletes your sign-in and saved library, and tells Google to cancel the permission; asks you to confirm first | It is destructive and cannot be undone, so it asks. If Google cannot be reached it still deletes locally and tells you how to finish at myaccount.google.com. |
| **Typed errors vs partial results** | If something worked, you get a *partial* result; if nothing worked, you get a clear error | A sync that saved 90% of your library and failed on one playlist is useful. It should say so, not look like a total failure. |

## 4. How we built it: the spec-first loop in practice

Week 0 introduced the idea: **write the spec, review it, then let the agent build**. Week 1 is where you can see how much that pays off. The U1 spec went through four versions before a line of code existed.

| Version | What changed it | Examples of what it fixed |
|---|---|---|
| v1 | First draft from the requirements document | The basic shape of the unit |
| v2 | Your two decisions (library scope, shared data) and a review of the draft | A big gap: "library" was undefined and could mean thousands of videos. The incremental-sync rule was wrong. |
| v3 | A list of 28 ambiguities I raised, answered in bulk | Where data lives, how retries and quota work, what each command prints, what the exit codes mean, how locks and backups work |
| v4 | A second pass that found 6 contradictions and 12 smaller details | The email-versus-permission conflict, a command that could not work before the first sync, a missing playlist-name table, a rule that blocked future units from cleaning old data |

Between v2 and v3, an **independent reviewer** (a separate agent that had not seen my reasoning) read all the specs and found 13 problems, which I checked against the files and the Google documentation before fixing. This matters because the author of a spec is the worst person to find its gaps.

> **PM lesson:** Every ambiguity you leave in a spec is a decision you are handing to the agent without realizing it. Finding them by *asking "what would the agent have to guess?"* is cheaper than finding them in code review. In this unit, the review found problems that would each have cost a day of rework.

## 5. What the reviews caught, in plain terms

Some real examples, so you can see what a good review looks like:

- **A permission contradiction.** The spec said "read-only access only" and also "store the Google email". Those cannot both be true. Reading an email needs a second permission.
- **A command that could not work.** `channels list` was meant to show your subscriptions, but subscriptions only arrived during a sync. Run on day one, the list would have been empty.
- **A fact that was simply wrong.** My spec said YouTube search costs 100 quota units. When I checked Google's page (twice), it said something different. The number was fixed, and the rule "never call search" stayed.
- **A rule that would block the future.** The purge command (delete old video details) had to avoid deleting videos that later units depend on. The fix was to make the *database* protect them, so U2 and U3 did not need to be named in U1.
- **Numbers that could not work together (for U2).** The matching score weights could never reach the "matched" threshold when titles differed. That is now written down, to be tuned on real data.

## 6. Testing: what was checked, and what cannot be

**Automated tests (108 pass).** They run in under a second and use a **fake YouTube** instead of the real one. Examples:

- A playlist that fails halfway removes nothing.
- A video in two sources stays when one source drops it.
- Sync run twice gives the same result and makes no detail lookups the second time.
- A wrong permission is refused and nothing is saved.
- Log files never contain tokens, even inside error messages.
- A killed sync does not leave a stuck lock.
- A simulated library of 200 subscriptions, 20 playlists and 2,000 items syncs within the speed target, using a fake that charges 0.3 seconds per call.

**Manual validation on your real account.** You ran the real thing:

| What | Result |
|---|---|
| First sync | 6.3 seconds and 20 quota units, out of 10,000 a day |
| Liked videos | 166 found, 150 added, 16 skipped as deleted or private |
| Three marked channels | 50 episodes each |
| Second sync | No detail lookups, 13 quota units |
| Removing a playlist item on YouTube | Removed from the library at the next sync |
| Your 20 seed episodes | All 20 found, none unavailable |
| Search of code and logs for secrets | Nothing found |

**What the tests cannot prove.** The fake YouTube is hand-written, so the tests cannot tell if Google changes how its responses look. Real syncs prove today's shape is right, but the saved real-response samples (validation step 17) were deferred. This is recorded as a known limit, not hidden.

> **PM lesson:** Tests and real-world validation catch different things. Tests catch *regressions* (something that used to work breaks). Real use catches *surprises*. You need both, and you should write down what neither covers.

## 7. Surprises from the real world

Plans meet reality on the first real run. Week 1 had several:

- **None of your seed podcasts were subscriptions.** Lenny's Podcast, Greg Isenberg and Raj Shamani entered your library through Liked videos. After you subscribed, they also arrive through their channels. This exposed a limit of decision D9: only subscribed channels can be marked. Whether to allow "mark any channel by ID" is open for v1.1.
- **Sync is cheap.** 20 quota units out of 10,000. The worry that sync might exhaust the daily allowance does not apply at your size.
- **You own no playlists** at the start, so playlist handling was tested with a test playlist you created on the YouTube website. (The app cannot create or change anything on YouTube, by design.)
- **A confusing `status`.** After you ran `revoke` and signed in again, `status` correctly said "no sync yet" and "0 videos". It looked like a bug and cost a round of diagnosis. The system was right: revoke deletes your library on purpose. Lesson: a message that is correct but surprising still needs a clearer explanation (a candidate improvement).
- **Your data folder was too open.** It was created in Week 0 with default permissions. The app now tightens it to private on first run and tells you. The same fix was then applied to the log folder, after you spotted it.
- **Shared data survives revoke.** Revoke deletes everything *about you*, but the shared video details stay, which is why the database file stayed large. That follows decision D10, and is worth explaining to testers.

## 8. Mistakes made along the way

Being honest about errors is part of the process:

- **A wrong number in my own spec** (the search cost), caught by checking the source.
- **Two lint rounds.** After the code passed 107 tests, your lint check found 43 style issues, then 2 more. Some were cosmetic. A few were real: a loop variable captured loosely in a lambda, and two tests that caught "any exception" instead of the exact one. I could not run the linter in my environment, so your terminal was the real check.
- **Two test bugs** were in my tests, not the code: one assumed a page number that did not exist, and one test URL "not-a-video" happened to look like a valid 11-character ID.
- **I stripped a few "ignore this lint rule" comments too eagerly,** and two of them were needed. The linter told us immediately.

None of these reached your real data. Automated checks (tests, lint) existed to catch exactly this kind of slip.

## 9. Lessons for you as a PM

1. **Define the nouns first.** "Library" meant three different things until D9 pinned it down. Most scope disasters start with an undefined word.
2. **Make failure safe, not just rare.** The safe-removal rule is the difference between "sync fails" and "sync deletes your data". Ask of every feature: *what is the worst thing this does when it half-works?*
3. **Smallest permission that works.** Ask for read-only. It also made the product easier to explain to anyone you ask to try it.
4. **Specs get better in rounds.** Four versions before code felt slow, and saved days of rework. Independent review beat self-review.
5. **Write down what you did not test.** The deferred step 17 is in the record, with the reason.
6. **Real data beats imagination.** The first real sync told us more about the library than all the planning did. Run early.
7. **Don't read dashboards, read decisions.** The decision log (`decisions.md`) is the part of the repo you will actually use in six months.

## 10. Where things stand

| Item | Status |
|---|---|
| U1 YouTube connector | Done and validated (steps 1–16 passed, step 17 deferred) |
| Tests and lint | 108 tests pass, lint clean |
| Week 1 as planned | **Only U1 is done.** U2 (episode resolver) and U3 (transcription) are still to build |
| YouTube storage rules | Your task: read YouTube's API developer policies on how long stored data may be kept, and record it under D10 |
| Open decisions | D2 (videos with no feed), D5, D6, D8, D11 (languages, including Hindi content) |

**Next:** merge U1 into `main`, then start U2 with a small probe of the Podcast Index episode lookups, because their paging rules are still unverified.

## 11. New terms (adds to the Week 0 glossary)

| Term | Plain meaning |
|---|---|
| **Quota (units)** | YouTube's daily allowance for API calls. Each simple read costs 1 unit, and you have 10,000 a day. |
| **Scope / least privilege** | The specific permission an app asks for. Ask for the smallest one that does the job. |
| **Refresh token** | A long-lived key that lets the app stay signed in without asking you again. Stored in your Mac's Keychain, never in a file. |
| **Keychain** | The macOS password vault. |
| **Idempotent** | Doing it twice has the same result as doing it once. A good sync is idempotent. |
| **Source** | One place videos come from: Liked, a playlist or a channel. |
| **Cumulative** | Items stay once added, even as the source changes. Used for podcast channels. |
| **Partial result** | The run saved some work but not all. Reported clearly, not hidden. |
| **Typed error** | A clearly named failure ("not signed in", "quota used up") that code and people can handle differently. |
| **Foreign key** | A database rule that stops you deleting something another table still points to. |
| **Migration** | A numbered, one-way change to the database layout, applied automatically and backed up first. |
| **Shared vs per-user data** | Episode details are stored once for everyone. Your library and tokens belong to you. |
| **Lock (file lock)** | A marker that stops two syncs from running at once. The operating system removes it if the program dies. |
| **Redaction** | Automatically blanking out secrets (tokens, emails) before anything is written to a log. |
| **Fake / mock** | A stand-in for a real service used in tests. Fast and predictable, but only as good as it matches the real thing. |
| **Regression** | Something that used to work and breaks after a change. Automated tests exist mainly to catch these. |
| **Exit code** | A number a command returns: 0 success, 1 error, 2 partial, 3 sign-in needed. |
| **CLI** | Command-line interface: the app used by typing commands. |
| **Lint** | An automatic style and mistake checker for code. |
