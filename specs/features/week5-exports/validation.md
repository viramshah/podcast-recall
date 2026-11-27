# Week 5: Validation (v1)

Run yourself before merging. You need a few saved findings: run `uv run podcast-recall serve`, ask two or three questions, click **Save finding** on each (one with a note you add later, one you mark 👎 first).

| # | Step | Expected |
|---|---|---|
| 1 | `uv run pytest -q` and `uv run ruff check .` | All tests pass, lint clean |
| 2 | `uv run podcast-recall findings list` | Your saved findings, newest first |
| 3 | `uv run podcast-recall findings note 1 "for the deck"` then `findings show 1` | The note appears in the printed export |
| 4 | `uv run podcast-recall findings export --format md` | "Wrote N finding(s) to ~/Documents/Podcast Recall exports/podcast-recall-findings.md"; the file opens in a text editor, quote first, then source and link, then "AI summary (may say more than the quote)" |
| 5 | Run step 4 again, then `ls -l ~/Documents/"Podcast Recall exports"` | Same single file, same size (no duplicate) |
| 6 | `uv run podcast-recall findings export --format html`, then AirDrop or save the `.html` to your iPhone (Files app) and open it in Safari | Readable on the phone, text fits the screen, no zooming needed |
| 7 | On the iPhone, tap **Open at this moment** on two findings | The YouTube app or Safari opens the video about 10 seconds before the quote; the quote is said within the next few seconds |
| 8 | On the Mac, open the same HTML file in Safari and Chrome and click two links | Same result |
| 9 | If you have an Android device or a friend with one: open the HTML file and tap two links | Links open at the right moment; otherwise record "Android untested" in `results.md` |
| 10 | `uv run podcast-recall findings export --format notes` (first run: allow your terminal to control Notes when macOS asks) | A note named "Podcast Recall findings" appears; open Notes on the iPhone after iCloud syncs and check the links |
| 11 | Run step 10 again | The same note is updated, not a second note |
| 12 | `uv run podcast-recall findings delete 1`, then export again | The deleted finding is gone from the file and the note |
| 13 | In the web chat, use **Download Markdown** and **Download HTML** in the Saved findings section; edit a note; delete a finding | Files download; list updates |
| 14 | Put a plain text file called `mine.md` in the export folder and run `findings export --out ~/Documents/"Podcast Recall exports"/mine.md` | Refused ("was not made by Podcast Recall"); your file is untouched |
| 15 | Check `git status` | No export files, answers files or transcript text tracked |

Record the device results (iPhone model and iOS, Mac, Android or "untested") in `results.md`, then write `docs/Week5_Explained.md` and merge.
