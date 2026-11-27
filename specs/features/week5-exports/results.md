# Week 5 results (exports)

Status: **complete. Device checks reported done by Viram on 2026-11-27 ("It works totally fine"); the details of each result were not sent to the assistant.**

## Automated checks
- Full suite: 611 passed, `ruff check .` clean. 21 new tests in `tests/test_exports.py`.
- Covered: quote-first layout with the labelled AI summary; exact links (video id and start minus 10 s, never negative); newest first; `--since` and `--show` filters; HTML escaping and Markdown neutralising of hostile text; a bad video id gets no link; warnings (premise corrected, removed claims, marked not helpful); byte-identical re-export and one file only; file mode 600; a file without the marker is never overwritten without `--force`; per-user edit and delete; Apple Notes text passed as an argument not in the script, Mac-only and a clear error when Notes refuses; CLI commands; web download (token required, attachment, correct types, nosniff), list, edit note, delete.

## Not yet verified (needs the PM's devices)
Validation steps 6 to 11 in `validation.md`: HTML on an iPhone, links on iOS, Mac and (if available) Android, and the Apple Notes note syncing to the iPhone. The Apple Notes script was never run here (the development sandbox cannot open Notes).

## Device results
- Validation steps 1 to 14 were run by the PM, who reported that everything works. This covers Markdown and HTML export, no duplicates on re-export, the HTML file opening on an iPhone with working links, the Mac browsers, the Apple Notes note (created and updated in place), delete, and the foreign-file protection.
- **Not recorded** (the PM did not send them): the iPhone model and iOS version, the exact link behaviour per device, and whether Android was tested. Android is therefore recorded as **untested**. Add the device details here if you want them in the record.

## Gate (from requirements.md)
| Gate item | Result |
|---|---|
| Markdown and HTML export open on a phone, links jump to the right moment | **Met** (reported by the PM) |
| Apple Notes export syncs to the iPhone | **Met** (reported by the PM) |
| Re-export gives no duplicates | **Met** (automated test and PM check) |
| Quote first, AI summary labelled, warnings carried | **Met** (automated tests) |
| CLI `findings` commands and web download | **Met** (automated tests, PM check) |
| iPhone and Mac tested; Android if a device exists | iPhone and Mac reported; Android untested |
| No new network calls | **Met** (exports are generated locally) |
