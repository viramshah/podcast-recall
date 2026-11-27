# Podcast Recall

*Week 5 (exports: getting findings out of the app and onto your phone) explained for a product manager learning to build agents*

Owner: Viram Shah  |  Written: Nov 27, 2026  |  Companion to docs/Week4_Explained.md, specs/decisions.md (D25) and specs/features/week5-exports/

> **How to read this:** Same style as the earlier guides: no coding knowledge assumed, new words explained when they first appear, a glossary at the end. Week 5 was smaller and calmer than Week 4, and that is itself a lesson: after a week of measuring quality, a week of shipping something people can touch. It covers what was built, the decisions behind it, and what this week taught about turning an AI answer into something that lives outside the app.

## 1. What Week 5 is, in plain English

The app can answer a question and show a real quote with a link. But an answer in a browser tab disappears. The reason to build the tool is to find something you heard, and then **use it**: in a deck, a note, a message. Week 5 builds the last step: **save a finding, and export it so it is on your phone.**

Three ways out, in order of effort:
1. **Markdown**, a plain text file any note or editor opens.
2. **HTML**, one web page in a single file. It opens on a phone in Safari or Chrome with nothing to install.
3. **Apple Notes**, one note that syncs to your iPhone through iCloud on its own.

The gate: **findings open on a phone with working links.** Your testing on the iPhone and the Mac showed it works.

## 2. What an exported finding looks like, and why

| Part | What it shows | Why |
|---|---|---|
| The question | As the heading | So you remember why you saved it |
| **The quote** | The verified transcript text, first | The quote is the part we can prove is real |
| Source and time | Show, episode, and the time, with a link that opens the video 10 seconds early | You can jump to the moment and hear the lead-in |
| **The AI summary** | Labelled "AI summary (may say more than the quote)" | Week 4 showed the summary often says more than its quote |
| A warning, if any | "The question assumed something the podcasts do not say", "a statement was removed", "you marked this not helpful" | An export outlives the app, so the warnings have to travel with it |
| Your note and the date | As you wrote them | Context you will want later |

**The big idea:** this is the Week 4 finding, applied. The quote leads and the AI sentence follows with a label, so what you carry out of the app is the part we can verify.

## 3. The decisions and the reasons behind them

| Decision | What we chose | Why |
|---|---|---|
| **Formats** | Markdown, HTML and Apple Notes this week; Google Docs later; Notion cut | The first three need no accounts. Google Docs needs a login and a choice of account, so it waits for Week 6 |
| **HTML as its own format** | One self-contained file | Markdown does not display on a phone without an app |
| **One collection, newest first** | Filters by date (`--since`) and show (`--show`) | Simple now; named collections can come later |
| **Re-export rewrites the same file** | The file or note is rebuilt from the findings each time | It cannot create duplicates, because it never adds, it replaces |
| **One Apple Note, updated in place** | Found by its name | Many small notes would clutter the Notes app |
| **Files stay private** | Written to `~/Documents/Podcast Recall exports/`, readable only by you, never overwriting a file the tool did not create | Exports hold your questions and quotes |
| **Links** | `https://youtu.be/<id>?t=<seconds>`, plus the time as visible text | If an app ignores the time, you can still scrub to it |
| **Findings can be edited and deleted** | The note, yes; the quote and answer, never | You fix mistakes without rewriting what was said |
| **A thumbs-down answer can still be saved** | It is exported marked "not helpful" | An honest record, not a hidden one |

## 4. How it was built and kept safe

The exporter is one piece of code that turns a list of findings into text. Markdown, HTML and the Apple Notes version all come from the same list, so they cannot disagree. Four properties are protected by tests:

- **Untrusted text stays inert.** Quotes come from other people's speech and the notes are yours, so a bad character could in theory become a script or a fake link. HTML is escaped, Markdown is neutralised, and a link is written only for a valid 11-character video id.
- **Every link is checked** against the stored citation, automatically, on every export in the tests.
- **Re-export is byte-for-byte identical.** The export never includes the time it was made, so running it twice gives the same file.
- **Apple Notes gets the text as an argument, not pasted into the script,** so a quote cannot change what the script does.

The sandbox used for development cannot open Notes, so that part was built with a stand-in and then verified by you on your Mac.

## 5. What this week taught as a PM

1. **A feature is not finished until it works where the user is.** Opening a file on the phone is the gate, not "the export runs".
2. **Carry the warnings with the data.** Once an answer leaves the app, the app's caveats stay behind unless you write them into the export.
3. **Make re-running safe.** Replacing instead of appending removes a whole class of "why do I have three copies" bugs.
4. **Pick the boring path that already works.** Markdown, HTML and Apple Notes needed no accounts and no network. Google Docs would have added a login and a security review for little extra value this week.
5. **Test the thing a hostile input can reach.** The export is the first place the app writes transcript text into other formats, so it is where escaping mattered most.

## 6. Still open

- **Google Docs export** (needs a login and a choice of Google account) and **Notion** (v1.1).
- **Android:** not tested; the plain https links should behave the same, but that is unconfirmed.
- **Device details** for the record (iPhone model, iOS version, exactly how each link behaved) were not written down.
- **From Week 4, still unresolved:** claim support (the summary can say more than its quote), a human check of the claims, your own 20 questions, and the decision on the quality bar before testers see anything.
- **Next: Week 6,** testers: sharing the app with up to four people, which needs a sign-in decision and a re-decision of the quality gate.

## Glossary

| Term | Meaning |
|---|---|
| **Finding** | An answer you saved, with its question, quotes, summary, your note and the date |
| **Export** | Writing findings into a file or note outside the app |
| **Markdown** | A plain-text format with simple marks for headings and quotes |
| **HTML** | The format of a web page; here, one self-contained file that opens on a phone |
| **Apple Notes export** | A single note, created or updated on your Mac, that syncs to your iPhone through iCloud |
| **Re-export** | Exporting again after changes; here it replaces the old file or note instead of adding to it |
| **Escaping** | Turning characters that could act like code into harmless text |
| **Idempotent** | Doing it twice gives the same result as doing it once |
| **Deep link** | A web address that opens a video at a particular second |
