# Week 5: Exports (U7), Requirements (v2, 2026-11-26)

Branch: `feature/week5-exports` (from `main` after Week 4 was merged). Depends on Week 3 (findings are saved from the web chat: table `findings`, `core.save_finding`, `core.list_findings`) and Week 4 (the quote-first display and the AI-summary label, D22). Roadmap gate: **findings open on a phone with working links.**

Status: **v2. All 14 questions at the end are decided (every recommendation applied, 2026-11-26; decision D25).**

## Where we start
- A user can already **save a finding** from the web chat (the question, the whole answer with its verified quotes, an optional note, the saved time). Nothing reads findings back out except `core.list_findings`. There is no export, no `findings` command and no way to delete or edit a finding.
- Every citation already carries a **link that opens the video 10 seconds before the quote** (`https://youtu.be/<id>?t=<seconds>`), built and tested in Week 3.
- Week 4's lesson applies: an answer's quote is verified text, the AI sentence about it may say more than the quote. An export must keep that distinction visible, because exported notes outlive the app's warnings.

## What done looks like (the Week 5 gate)
1. **Export to Markdown and to a single self-contained HTML page** for a chosen set of findings, written to a folder on the Mac. Both open on a phone (iPhone first) with every link jumping to the right moment.
2. **Export to Apple Notes** (AppleScript, local only), so findings sync to the iPhone through iCloud without any account setup.
3. **Re-export never creates duplicates:** exporting the same findings twice gives the same file or the same note, updated in place.
4. **Each exported finding shows, in this order:** the question, the verified quote or quotes (quote-first), the show and episode with the timestamp, the link, the AI summary labelled "AI summary (may say more than the quote)", the user's note, and the saved date.
5. **`findings` commands in the CLI** (`list`, `show`, `delete`, `export`) and an **Export** button in the web chat that downloads the Markdown or HTML file. The existing Host, Origin and token protections apply.
6. **Tested on devices:** iPhone and the Mac desktop required; Android if a device is available (Q10). Every link in the export is checked automatically against the stored citation (video id and start second), and checked by hand on the devices.
7. Zero new network calls: exports are generated locally from the database. (Google Docs and Notion are not in this gate: Q1.)

## Out of scope this week
- Notion export (v1.1, per the plan's cut line).
- Google Docs export unless Q1 is answered "include it".
- Sharing a finding with another person, a public page, or editing quotes.
- Changing how answers are produced or scored.

## Design notes (proposed)
- **One exporter function takes a list of findings and a format and returns text**; the CLI, the web button and the Apple Notes writer all call it. Markdown and HTML are built from the same internal structure so they cannot disagree.
- **Escaping:** transcript text is untrusted. HTML output escapes everything, Markdown output escapes link and formatting characters in quotes and notes, and links are only written for valid 11-character video ids with an integer start second.
- **Apple Notes:** the export script sends the note body through AppleScript from the app only when run on macOS; the sandbox used for development cannot open Notes, so the Apple Notes step is verified on the PM's Mac and the code is covered by tests that fake the script runner.
- **Privacy:** exports contain the user's questions and short transcript quotes. They are written only where the user points (default `~/Documents/Podcast Recall exports/`), with file mode 600, never inside the repo, never uploaded. Revoking an account deletes the database rows, not files already exported; the README says so.
- **Stable identity:** each exported finding carries its finding id, so a re-export updates and a delete is reflected on the next export.

## Decisions (14), all recommendations applied (D25)
1. **Which export targets this week, and in which order?** (a) Markdown, HTML, Apple Notes; Google Docs if time; Notion cut. (b) All four. (c) Markdown only. **Recommendation: (a).** Markdown and HTML need no accounts; Apple Notes reaches the iPhone with no setup. Google Docs needs an OAuth client and a decision about which Google account (personal or work), so it waits for Week 6's OAuth work.
2. **Is HTML a separate format from Markdown?** Markdown does not render on a phone without an app. **Recommendation: yes, one self-contained HTML file** (no external fonts, scripts or images) that opens in Safari or Chrome from Files, email or AirDrop.
3. **What counts as a "collection"?** (a) Everything saved, newest first. (b) A named collection the user chooses when saving. (c) Filter by date range or show at export time. **Recommendation: (a) plus (c)** (`--since`, `--show`); named collections wait for v1.1.
4. **Layout of one finding?** **Recommendation: quote first, then source and link, then the labelled AI summary, then the note** (D22). The question is the heading.
5. **Show warnings in exports?** The exported note will outlive the app, so a finding whose answer was `premise_corrected` or had a removed claim should say so. **Recommendation: yes**, one short line, same words as the app.
6. **Re-export behaviour?** (a) Rewrite the whole file or note each time. (b) Append only new findings. **Recommendation: (a).** Whole-file regeneration cannot duplicate; the file name is stable per filter (`podcast-recall-findings.md`).
7. **Apple Notes: one note per finding or one note for the collection?** **Recommendation: one note named "Podcast Recall findings", rewritten in place** (found by exact name), because per-finding notes clutter the Notes app and updates are harder to dedupe.
8. **Where do export files go, and how are they protected?** **Recommendation: `~/Documents/Podcast Recall exports/` by default, `--out` to override, file mode 600, refuse to overwrite a file the tool did not create** (marker line in the file) unless `--force`.
9. **Link format?** **Recommendation: keep `https://youtu.be/<id>?t=<seconds>` opening 10 s early; also print the timestamp as text** (so the user can scrub if the app ignores `t=`).
10. **Which devices must pass?** **Recommendation: iPhone (Safari and the YouTube app) and Mac required; Android only if you have a device or borrow one**; otherwise record it as untested and keep the plain-https links, which are the part that behaves the same everywhere.
11. **Can a finding be edited or deleted?** **Recommendation: edit the note and delete the finding from the CLI and the web chat** (small, needed to fix mistakes). The quote and answer are never editable.
12. **Should a thumbs-down answer be savable?** **Recommendation: yes, but exported with a line "marked as not helpful"** so the note is honest. (Today the app lets you save any answered question.)
13. **Web export UI?** **Recommendation: a small Export section on the page with two buttons (Markdown, HTML) that download the file for the saved findings.** The CLI is the full interface.
14. **How do we prove the exports are right?** **Recommendation:** (a) golden-file tests for the Markdown and HTML of two fixed findings; (b) a link test that parses every link in the export and checks it equals the stored citation (video id, start second minus 10); (c) an escaping test with hostile transcript text; (d) a re-export test (twice gives byte-identical output); (e) the device check as manual steps in `validation.md`.
