"""Turning saved findings into files and notes (Week 5, decision D25).

One list of `ExportItem`s is rendered three ways: Markdown, a single self-contained HTML page (opens
on a phone) and an HTML fragment for Apple Notes. Rules that matter:
- Quote first, then where it is from and the link, then the AI sentence labelled as such (D22).
- Transcript text and the user's words are untrusted: HTML is escaped, Markdown is escaped, and a
  link is written only for a valid 11-character video id and a whole number of seconds.
- The output depends only on the findings, never on the clock, so exporting twice gives the same
  bytes and a re-export cannot create duplicates.
- Files are written with mode 600 and a marker line; a file without the marker is never overwritten
  unless the caller says so.
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from podcast_recall.answers import Answer, Citation, link_for, parse_answer
from podcast_recall.errors import ConfigError
from podcast_recall.golden import format_time

MARKER = "podcast-recall export"
FORMATS = ("md", "html")
TITLE = "Podcast Recall findings"
SUMMARY_LABEL = "AI summary (may say more than the quote)"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>()#+!|~])")
MAX_NOTE = 1000


@dataclass(frozen=True)
class ExportItem:
    finding_id: int
    question: str
    answer: Answer
    note: str
    saved_at: str
    not_helpful: bool = False
    removed_claims: int = 0


def safe_link(citation: Citation) -> str | None:
    """The link for a citation, rebuilt from its parts. None when the video id is not valid."""
    if not VIDEO_ID.match(citation.video_id or ""):
        return None
    return link_for(citation.video_id, citation.start_s)


def warnings_for(item: ExportItem) -> list[str]:
    found: list[str] = []
    if item.answer.status == "premise_corrected":
        found.append("The question assumed something the podcasts do not say.")
    if item.removed_claims:
        word = "statement was" if item.removed_claims == 1 else "statements were"
        found.append(f"{item.removed_claims} {word} removed because its quote could not be verified.")
    if item.not_helpful:
        found.append("You marked this answer as not helpful.")
    return found


# ---------------------------------------------------------------------------- loading


def load_items(
    conn: sqlite3.Connection, user_id: str, since: str | None = None, show: str | None = None
) -> list[ExportItem]:
    rows = conn.execute(
        "SELECT f.finding_id, f.request_id, f.question, f.answer_json, f.note, f.saved_at, "
        "COALESCE(r.claims_dropped, 0) AS dropped, "
        "EXISTS (SELECT 1 FROM feedback b WHERE b.request_id = f.request_id AND b.thumbs = -1) AS down "
        "FROM findings f LEFT JOIN answer_requests r ON r.request_id = f.request_id "
        "WHERE f.user_id = ? ORDER BY f.saved_at DESC, f.finding_id DESC",
        (user_id,),
    ).fetchall()
    items: list[ExportItem] = []
    for row in rows:
        if since and row["saved_at"][:10] < since:
            continue
        answer = parse_answer(json.loads(row["answer_json"]))
        if show and not any(show.lower() in c.show.lower() for cl in answer.claims for c in cl.citations):
            continue
        items.append(ExportItem(
            row["finding_id"], row["question"], answer, row["note"], row["saved_at"],
            bool(row["down"]), int(row["dropped"]),
        ))
    return items


# ---------------------------------------------------------------------------- Markdown


def md_escape(text: str) -> str:
    """Make untrusted text inert in Markdown: one line, special characters escaped."""
    return _MD_SPECIAL.sub(r"\\\1", " ".join((text or "").split()))


def _md_quote_lines(text: str) -> list[str]:
    return [f"> {md_escape(line)}" for line in (text or "").splitlines() if line.strip()] or ["> "]


def render_markdown(items: Sequence[ExportItem]) -> str:
    lines = [f"<!-- {MARKER} -->", f"# {TITLE}", "", f"{len(items)} finding{'s' if len(items) != 1 else ''}, newest first.", ""]
    for item in items:
        lines += [f"## {md_escape(item.question)}", f"_Saved {item.saved_at[:10]}. Finding {item.finding_id}._", ""]
        for warning in warnings_for(item):
            lines += [f"**Note:** {md_escape(warning)}", ""]
        if item.answer.status == "premise_corrected" and item.answer.summary:
            lines += [f"{md_escape(item.answer.summary)} _(explanation, not a quote)_", ""]
        for number, claim in enumerate(item.answer.claims, 1):
            for cite in claim.citations:
                lines += _md_quote_lines(cite.quote)
                link = safe_link(cite)
                where = f"{md_escape(cite.show)}: {md_escape(cite.title)}, at {format_time(cite.start_s)}"
                lines += ["", f"{where} ([open at this moment]({link}))" if link else where, ""]
            lines += [f"_{SUMMARY_LABEL}:_ {md_escape(claim.text)}", ""]
        if item.note.strip():
            lines += [f"**My note:** {md_escape(item.note.strip()[:MAX_NOTE])}", ""]
        lines += ["---", ""]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------- HTML

_CSS = (
    "body{font-family:-apple-system,system-ui,Segoe UI,Roboto,sans-serif;max-width:42rem;margin:0 auto;"
    "padding:1rem;line-height:1.45;color:#1a1a1a}h1{font-size:1.4rem}h2{font-size:1.1rem;margin:1.6rem 0 .2rem}"
    ".meta{color:#666;font-size:.85rem}blockquote{margin:.6rem 0 .2rem;padding:.4rem .8rem;border-left:4px solid #bbb;"
    "background:#f6f6f6;font-style:italic}.src{font-size:.9rem;color:#444;margin:0 0 .5rem}"
    ".sum{font-size:.92rem;color:#444;margin:.2rem 0 .8rem}.tag{font-weight:600;color:#666}"
    ".warn{background:#fff6e0;border:1px solid #f0d58a;padding:.4rem .6rem;border-radius:6px;margin:.4rem 0;font-size:.9rem}"
    ".note{background:#eef5ff;padding:.4rem .6rem;border-radius:6px}hr{border:0;border-top:1px solid #ddd;margin:1.4rem 0}"
    "a{color:#0b57d0}"
)


def _e(text: str) -> str:
    return html.escape(text or "", quote=True)


def _html_items(items: Sequence[ExportItem]) -> list[str]:
    out: list[str] = []
    for item in items:
        out.append(f"<h2>{_e(item.question)}</h2>")
        out.append(f'<div class="meta">Saved {_e(item.saved_at[:10])}. Finding {item.finding_id}.</div>')
        for warning in warnings_for(item):
            out.append(f'<div class="warn"><b>Note:</b> {_e(warning)}</div>')
        if item.answer.status == "premise_corrected" and item.answer.summary:
            out.append(f"<p>{_e(item.answer.summary)} <i>(explanation, not a quote)</i></p>")
        for claim in item.answer.claims:
            for cite in claim.citations:
                out.append(f"<blockquote>&ldquo;{_e(cite.quote)}&rdquo;</blockquote>")
                link = safe_link(cite)
                where = f"{_e(cite.show)}: {_e(cite.title)}, at {_e(format_time(cite.start_s))}"
                if link:
                    where += f' <a href="{_e(link)}" rel="noopener noreferrer">Open at this moment</a>'
                out.append(f'<p class="src">{where}</p>')
            out.append(f'<p class="sum"><span class="tag">{_e(SUMMARY_LABEL)}:</span> {_e(claim.text)}</p>')
        if item.note.strip():
            out.append(f'<p class="note"><b>My note:</b> {_e(item.note.strip()[:MAX_NOTE])}</p>')
        out.append("<hr>")
    return out


def render_html(items: Sequence[ExportItem]) -> str:
    count = f"{len(items)} finding{'s' if len(items) != 1 else ''}, newest first."
    body = [f"<h1>{_e(TITLE)}</h1>", f'<div class="meta">{_e(count)}</div>'] + _html_items(items)
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="en"><head><meta charset="utf-8"><!-- {MARKER} -->'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_e(TITLE)}</title><style>{_CSS}</style></head><body>\n" + "\n".join(body) + "\n</body></html>\n"
    )


def render_notes_html(items: Sequence[ExportItem]) -> str:
    """The body of the Apple Notes note: the title first (Notes uses it as the name), no styles."""
    count = f"{len(items)} finding{'s' if len(items) != 1 else ''}, newest first."
    return f"<h1>{_e(TITLE)}</h1><div>{_e(count)}</div>" + "".join(_html_items(items))


def render(items: Sequence[ExportItem], fmt: str) -> str:
    if fmt == "md":
        return render_markdown(items)
    if fmt == "html":
        return render_html(items)
    raise ConfigError(f"Unknown export format '{fmt}'. Use one of: {', '.join(FORMATS)}.")


# ---------------------------------------------------------------------------- files


def file_name(fmt: str, since: str | None = None, show: str | None = None) -> str:
    """A stable name per format and filter, so a re-export rewrites the same file."""
    parts = ["podcast-recall-findings"]
    if show:
        parts.append(re.sub(r"[^a-z0-9]+", "-", show.lower()).strip("-")[:40] or "show")
    if since:
        parts.append(f"since-{since}")
    return "-".join(parts) + f".{fmt}"


def write_export(path: str | Path, text: str, force: bool = False) -> Path:
    """Write the export with mode 600, replacing it atomically. A file that was not made by this tool
    (it lacks the marker) is never overwritten without `force`."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        existing = target.read_text(encoding="utf-8", errors="ignore")[:400]
        if MARKER not in existing:
            raise ConfigError(f"{target} exists and was not made by Podcast Recall. Choose another name or use --force.")
    fd, temp = tempfile.mkstemp(dir=str(target.parent), prefix=".export-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temp, 0o600)
        os.replace(temp, target)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return target
