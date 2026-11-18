# Podcast Recall

*Unit U2 (the episode resolver) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 17, 2026  |  Companion to docs/Week1_Explained.md, specs/decisions.md (D14) and specs/features/u2-episode-resolver/

> **How to read this:** Same style as the earlier guides. No coding knowledge assumed, and technical words are explained when they first appear. It covers what U2 does, **why each decision was made**, what the real data taught us, and what to take from it as a PM. A glossary is at the end.

## 1. What U2 is, in plain English

U1 knows which **YouTube videos** are in your library. But YouTube is a poor source of words: its captions are auto-generated and its audio cannot be downloaded cleanly. Podcasts, on the other hand, publish an **RSS feed**: a public list of every episode with its title, date, length, an audio link, and sometimes a transcript file.

U2 answers one question for every video: **"Which podcast episode is this video?"** It does this in four steps:

1. **Pick the feed.** For each YouTube channel, you choose which podcast feed belongs to it (or "none" if it is not a podcast, like a video-only channel).
2. **Fetch the episodes.** It downloads that feed's episode list from Podcast Index, a free directory of podcasts, once per feed, and stores it on your Mac.
3. **Match.** It compares each video with the feed's episodes and decides.
4. **Record the result**, with the reason, so a human can check it.

It does not download audio or transcribe. That is U3. U2 only produces a trustworthy list of "this video = this episode".

## 2. The four possible results

| Result | Meaning | What happens next |
|---|---|---|
| `matched` | Confident it is the same episode | U3 will transcribe it |
| `needs_review` | A plausible candidate, but not sure enough | Waits for you: `resolve confirm` or `resolve reject` |
| `unmatched` | A feed exists but no episode fits | Not transcribed |
| `no_feed` | The channel has no podcast feed (you chose "none") | Not transcribed |

The most important design rule: **a wrong match is worse than no match.** If the app links a video to the wrong episode, every quote it later shows would come from a different conversation, with a confident citation. So when in doubt, it asks you.

## 3. How a match is decided

For each video it scores every episode in the feed on three signals:

| Signal | Weight | What it looks at |
|---|---|---|
| Title | 50% | How much of the title text is shared |
| Date | 30% | Published within a day or so of the video |
| Length | 20% | Duration difference |

A combined score of **0.85 or more with a clear lead (0.15) over the second-best episode** is `matched`. Between 0.60 and that is `needs_review`. Below 0.60 is `unmatched`.

Two extra rules, both added because of real data:

- **Date-and-length lock.** Many channels rename a video on YouTube (a different title, a "Full Course" suffix, a guest's job title added). Titles then disagree, but the **same day and a length within 2% or 30 seconds** is almost impossible by chance. If exactly one episode fits both, it is `matched`.
- **Clip rule.** A short clip taken from a long episode has the right title and date, but its length is far shorter. A video much shorter than the episode is never matched, because its words are only part of that episode.

## 4. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **One lookup per feed, not per video** | Download a feed's whole episode list once, then match locally | Podcast Index asks for fair use. 20 videos used only 4 requests, and a re-run used none for unchanged feeds. |
| **You choose the feed per channel** | The app suggests candidates, you decide | Searching by name can return a similar show (for example a "Daily" version of Lenny's Podcast). A human choice once per channel is cheap and removes the biggest source of wrong matches. |
| **"None" is a real answer** | Channels with no podcast feed are stored as `no_feed` | Otherwise the app would keep searching, and might match a random show. |
| **Reviewed results are never overwritten** | If you confirm or reject a match, a later `resolve run` leaves it alone | Your judgement should beat the automatic one. Otherwise the same mistake would come back on every run. |
| **One result per video** | A video maps to at most one episode | Keeps downstream answers unambiguous. |
| **Credentials stay out of the repo** | Podcast Index key and secret come from the environment or a private file (permissions 600) | Same principle as U1: secrets are never committed or printed. We searched the whole git history for them to be sure. |
| **D14: starting numbers** | Weights 0.5/0.3/0.2, matched at 0.85, margin 0.15, review at 0.60 | We needed starting values. The seed run did not contradict them, so they stay, marked provisional. |

## 5. What the real data taught us

We ran it on your 20 seed videos:

- **16 matched, 1 unmatched, 3 no feed, 0 needs review.** The automatic result agreed with your hand-marked list on all 20 rows.
- **The date-and-length rule earned its place.** Seven of the 16 matches have a YouTube title that differs from the feed title (for example "84 minutes of enterprise sales alpha" versus "How to close $100K+ enterprise deals, step by step"). Title matching alone would have lost them. Date and length found them.
- **Lengths agree to the second.** Every match differed by 0 or 1 second between YouTube and the feed. Our "2% or 30 seconds" rule is far looser than needed for these shows. Shows that insert ads may differ more, which is why we left it loose and noted it to revisit.
- **The clip rule caught a mistake in our own list.** One seed row was a short clip from "Raj Shamani Clips", 5,632 seconds shorter than the full episode, and we had marked it as a full episode. The resolver correctly refused it. You replaced the URL with the full episode, and the second run matched it.
- **Dan Martell** correctly stayed `unmatched`: the feed we could reach did not contain that October video.

## 6. What went wrong along the way (and what we learned)

- **Pasting several commands into an interactive prompt.** The `resolve feeds` command asks questions. Pasted commands were consumed as answers. Lesson: for batch work, use a non-interactive command (`resolve set-feed`), and keep interactive prompts for a human at the keyboard.
- **The seed list itself had an error.** A test list is also a thing that can be wrong. The check found it, which is the point of checking.
- **Local `main` did not contain U2** when we started U3, because the merge had happened on GitHub only. Lesson: before starting the next unit, confirm your local `main` has the last one.

## 7. What to take from this as a PM

1. **Design for "I'm not sure."** Four result states, with a review queue, are what make a system you can trust. A two-state matched/not matched system would either guess or drop things.
2. **Prefer signals that are hard to fake.** Titles change; the same day plus the same length almost never coincides by accident. Look for the evidence that is expensive to get wrong.
3. **Test lists need testing too.** Your hand-marked answers are the ground truth only if they are right.
4. **Keep the human decision where it is cheap and high-value.** Choosing a feed once per channel took minutes and removed the main risk.
5. **Record why, not just what.** Every result stores its method and scores, so you can review it without guessing.

## 8. Still open

- Step 8 of the U2 validation (confirm one result by hand and run again) was left for you to try. It is a small check that your confirmation survives a re-run.
- Two matches rest on less title evidence than the rest (`st61aKW8P5A`, `1cWZ7Ekff6E`). Listening to the first minute of each would settle them.
- D14 numbers are provisional until a show with ads is in the set.

## Glossary

| Term | Meaning |
|---|---|
| **RSS feed** | A public list of a podcast's episodes that apps read to find new ones |
| **Podcast Index** | A free directory of podcasts, used here to find feeds and read their episode lists |
| **Resolver** | The part of the app that decides which episode a video is |
| **Match score** | A number from 0 to 1 combining title, date and length similarity |
| **Margin** | How far the best candidate's score is ahead of the second best |
| **Clip** | A short video cut from a longer episode |
| **Seed list** | Your 20 hand-picked videos with the right answers marked, used to test the app |
| **Reviewed** | A result a human confirmed or rejected, which automatic runs never overwrite |
