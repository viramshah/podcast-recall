# Week 5: Exports, Plan (v1, 2026-11-26)

Decisions: D25 (see `requirements.md`). Built in the order the requirements set.

1. **Exporter** (`podcast_recall/exporter.py`): one list of findings rendered as Markdown, a single HTML page and an Apple Notes fragment; output depends only on the findings, so a re-export is byte-identical; escaping and link rules in one place. Done.
2. **Findings store and core** (`requests_store.py`, `core.py`): get, delete and edit-note per user; `finding_items` joins the answer, thumbs-down feedback and removed-claim counts; `export_findings` and `export_findings_to_notes`. Done.
3. **CLI** (`findings list | show | note | delete | export --format md|html|notes`, `--since`, `--show`, `--out`, `--force`). Done.
4. **Web** (`GET /api/findings`, `GET /api/findings/export?format=md|html`, `PUT` and `DELETE /api/findings/<id>`; a Saved findings section with download buttons). Done.
5. **Apple Notes** (`podcast_recall/applenotes.py`): one note, created or updated in place; the text goes to AppleScript as an argument. Built with a fake script runner; the real run is a manual step on the Mac.
6. **Tests** (`tests/test_exports.py`, 21 tests): golden structure, newest first, filters, escaping, every link equals the stored citation, bad video id gets no link, warnings carried, idempotence, file mode 600, foreign files protected, per-user edit and delete, Apple Notes argument safety, CLI and web.
7. **Manual device checks** (`validation.md`).
