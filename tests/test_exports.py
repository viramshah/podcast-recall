"""Week 5: exporting saved findings (Markdown, HTML, Apple Notes) and managing findings."""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path

from podcast_recall import applenotes, core, exporter, paths, requests_store, store, web
from podcast_recall.answers import Answer, Citation, Claim
from podcast_recall.cli import main as cli_main
from podcast_recall.errors import ConfigError
from podcast_recall.golden import format_time
from tests.base import T0, Base
from tests.test_answers import PORT, TOKEN, call

HOSTILE = '<script>alert(1)</script> [click](javascript:alert(1)) **bold** & "quotes"'


def cite(video_id="abcdefghijk", start=125.0, quote="We ship on Fridays.", show="Show A", title="Episode 1"):
    return Citation(video_id, 1, show, title, quote, start, "u")


def answer(status="answered", quote="We ship on Fridays.", claim="They ship weekly.", **kwargs):
    return Answer(status, (Claim(claim, (cite(quote=quote, **kwargs),)),), "")


class Exports(Base):
    def add(self, question, ans, note="", saved="2026-11-20T10:00:00Z", dropped=0, thumbs=None, user="owner"):
        removed = [type("Dropped", (), {"reason": "r"})() for _ in range(dropped)]
        rid = requests_store.log_request(self.conn, user, question, ans, removed, [], "m", 1, T0)
        if thumbs:
            requests_store.add_feedback(self.conn, rid, user, thumbs, "", T0)
        fid = requests_store.add_finding(self.conn, rid, user, note, saved)
        return fid

    def test_markdown_is_quote_first_with_the_labelled_summary_and_exact_link(self):
        self.add("When do they ship?", answer(), note="for the deck")
        text = exporter.render_markdown(core.finding_items(conn=self.conn))
        self.assertIn(f"<!-- {exporter.MARKER} -->", text)
        self.assertLess(text.index("> We ship on Fridays."), text.index(exporter.SUMMARY_LABEL))
        self.assertIn("at 2:05 ([open at this moment](https://youtu.be/abcdefghijk?t=115))", text)
        self.assertIn("**My note:** for the deck", text)
        self.assertIn("Saved 2026-11-20", text)

    def test_newest_first_and_the_filters(self):
        a = self.add("older", answer(show="Show A"), saved="2026-11-01T00:00:00Z")
        b = self.add("newer", answer(show="Other Show"), saved="2026-11-25T00:00:00Z")
        ids = [i.finding_id for i in core.finding_items(conn=self.conn)]
        self.assertEqual(ids, [b, a])
        self.assertEqual([i.finding_id for i in core.finding_items(since="2026-11-10", conn=self.conn)], [b])
        self.assertEqual([i.finding_id for i in core.finding_items(show="show a", conn=self.conn)], [a])

    def test_html_is_self_contained_and_escapes_everything(self):
        self.add(HOSTILE, answer(quote=HOSTILE, claim=HOSTILE), note=HOSTILE)
        text = exporter.render_html(core.finding_items(conn=self.conn))
        self.assertNotIn("<script", text.lower())
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)
        self.assertIn('name="viewport"', text)
        self.assertEqual(re.findall(r'(?:src|href)="([^"]+)"', text), ["https://youtu.be/abcdefghijk?t=115"])

    def test_markdown_neutralises_links_and_formatting_in_untrusted_text(self):
        self.add(HOSTILE, answer(quote=HOSTILE, claim=HOSTILE), note=HOSTILE)
        text = exporter.render_markdown(core.finding_items(conn=self.conn))
        body = text.split("\n", 1)[1]  # after our own marker comment
        self.assertNotIn("](javascript:", body)
        content = "\n".join(line.removeprefix("> ") for line in body.splitlines())  # drop our quote markers
        self.assertEqual(re.findall(r"(?<!\\)[<>]", content), [])  # every angle bracket in the text is escaped
        self.assertNotIn("**bold**", body)

    def test_every_link_matches_the_stored_citation(self):
        self.add("q1", answer(start=500.4))
        self.add("q2", answer(start=3.0, quote="early quote"))
        items = core.finding_items(conn=self.conn)
        links = re.findall(r"\((https://youtu\.be/[^)]+)\)", exporter.render_markdown(items))
        expected = sorted(f"https://youtu.be/abcdefghijk?t={max(0, int(c.start_s) - 10)}"
                          for i in items for cl in i.answer.claims for c in cl.citations)
        self.assertEqual(sorted(links), expected)
        self.assertIn("?t=0", " ".join(links))  # a quote near the start never goes negative

    def test_a_bad_video_id_gets_no_link(self):
        bad = Answer("answered", (Claim("c", (cite(video_id='x" onmouseover="1'),)),), "")
        self.add("q", bad)
        md = exporter.render_markdown(core.finding_items(conn=self.conn))
        html = exporter.render_html(core.finding_items(conn=self.conn))
        self.assertNotIn("youtu.be", md + html)
        self.assertIn(format_time(125.0), md)

    def test_warnings_are_carried_into_the_export(self):
        ans = Answer("premise_corrected", (Claim("c", (cite(),)),), "The speaker said the opposite.")
        self.add("why?", ans, dropped=1, thumbs=-1)
        text = exporter.render_markdown(core.finding_items(conn=self.conn))
        for phrase in ("assumed something the podcasts do not say", "removed because its quote could not be verified",
                       "marked this answer as not helpful", "explanation, not a quote"):
            self.assertIn(phrase, text)

    def test_exporting_twice_gives_the_same_bytes_and_one_file(self):
        self.add("q", answer())
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        first, count = core.export_findings("md", out=str(folder), conn=self.conn)
        bytes1 = first.read_bytes()
        second, _ = core.export_findings("md", out=str(folder), conn=self.conn)
        self.assertEqual((first, count), (second, 1))
        self.assertEqual(bytes1, second.read_bytes())
        self.assertEqual(len(list(folder.iterdir())), 1)
        self.assertEqual(stat.S_IMODE(os.stat(first).st_mode), 0o600)

    def test_a_file_we_did_not_make_is_not_overwritten_without_force(self):
        self.add("q", answer())
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        target = folder / "mine.md"
        target.write_text("my own notes")
        with self.assertRaises(ConfigError):
            core.export_findings("md", out=str(target), conn=self.conn)
        self.assertEqual(target.read_text(), "my own notes")
        core.export_findings("md", out=str(target), force=True, conn=self.conn)
        self.assertIn(exporter.MARKER, target.read_text())

    def test_an_unknown_format_is_refused(self):
        with self.assertRaises(ConfigError):
            exporter.render([], "pdf")

    def test_file_names_are_stable_per_filter(self):
        self.assertEqual(exporter.file_name("md"), "podcast-recall-findings.md")
        self.assertEqual(exporter.file_name("html", "2026-11-01", "Lenny's Podcast"),
                         "podcast-recall-findings-lenny-s-podcast-since-2026-11-01.html")

    def test_delete_and_note_edit_are_per_user(self):
        store.upsert_user(self.conn, "other", "UCo", "Other", T0)
        fid = self.add("q", answer())
        core.update_finding_note(fid, "new note", conn=self.conn)
        self.assertEqual(core.list_findings(conn=self.conn)[0]["note"], "new note")
        with self.assertRaises(ConfigError):
            core.delete_finding(fid, user_id="other", conn=self.conn)
        core.delete_finding(fid, conn=self.conn)
        self.assertEqual(core.list_findings(conn=self.conn), [])
        self.assertEqual(core.finding_items(conn=self.conn), [])

    def test_apple_notes_gets_the_body_as_an_argument_not_in_the_script(self):
        calls = []

        def runner(command):
            calls.append(list(command))
            return type("R", (), {"returncode": 0, "stdout": "created\n", "stderr": ""})()

        self.add(HOSTILE, answer(quote=HOSTILE))
        result, count = core.export_findings_to_notes(conn=self.conn, runner=lambda c: runner(c))
        self.assertEqual((result, count), ("created", 1))
        command = calls[0]
        self.assertEqual(command[0], "osascript")
        self.assertNotIn("alert(1)", command[2])        # the script text
        self.assertIn("&lt;script&gt;", command[4])      # the escaped body travels as an argument
        self.assertEqual(command[3], exporter.TITLE)

    def test_apple_notes_only_on_a_mac_and_reports_a_refusal(self):
        with self.assertRaises(ConfigError):
            applenotes.write_note("<h1>x</h1>", runner=lambda c: None, platform="linux")
        failing = lambda c: type("R", (), {"returncode": 1, "stdout": "", "stderr": "not allowed"})()
        with self.assertRaises(ConfigError) as ctx:
            applenotes.write_note("<h1>x</h1>", runner=failing, platform="darwin")
        self.assertIn("Automation", str(ctx.exception))


class Commands(Base):
    def setUp(self):
        super().setUp()
        paths.ensure_data_home()
        self.file_conn = store.connect(paths.db_path(), paths.backup_dir())
        self.addCleanup(self.file_conn.close)
        store.upsert_user(self.file_conn, "owner", "UCme", "Me", T0)
        rid = requests_store.log_request(self.file_conn, "owner", "When do they ship?", answer(), [], [], "m", 1, T0)
        self.fid = requests_store.add_finding(self.file_conn, rid, "owner", "n", "2026-11-20T10:00:00Z")
        self.file_conn.commit()
        self.folder = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli_main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_list_show_note_export_and_delete(self):
        code, out, _ = self.run_cli("findings", "list")
        self.assertEqual(code, 0)
        self.assertIn("When do they ship?", out)
        self.assertIn("We ship on Fridays.", self.run_cli("findings", "show", str(self.fid))[1])
        self.assertEqual(self.run_cli("findings", "note", str(self.fid), "changed")[0], 0)
        target = Path(self.folder) / "out.html"
        code, out, _ = self.run_cli("findings", "export", "--format", "html", "--out", str(target))
        self.assertEqual(code, 0)
        self.assertIn("1 finding", out)
        self.assertIn("changed", target.read_text())
        self.assertEqual(self.run_cli("findings", "delete", str(self.fid))[0], 0)
        self.assertIn("No findings", self.run_cli("findings", "list")[1])

    def test_a_bad_since_date_and_a_missing_finding_are_clear_errors(self):
        code, _, err = self.run_cli("findings", "export", "--since", "yesterday")
        self.assertNotEqual(code, 0)
        self.assertIn("--since", err)
        code, _, err = self.run_cli("findings", "show", "999")
        self.assertNotEqual(code, 0)
        self.assertIn("no finding 999", err)

    def test_the_default_folder_can_be_moved_with_an_environment_setting(self):
        os.environ["PODCAST_RECALL_EXPORT_DIR"] = self.folder
        self.addCleanup(os.environ.pop, "PODCAST_RECALL_EXPORT_DIR", None)
        code, _out, _ = self.run_cli("findings", "export")
        self.assertEqual(code, 0)
        self.assertTrue((Path(self.folder) / "podcast-recall-findings.md").exists())


class WebExport(Base):
    def setUp(self):
        super().setUp()
        paths.ensure_data_home()
        self.file_conn = store.connect(paths.db_path(), paths.backup_dir())
        self.addCleanup(self.file_conn.close)
        store.upsert_user(self.file_conn, "owner", "UCme", "Me", T0)
        rid = requests_store.log_request(self.file_conn, "owner", "When do they ship?", answer(quote=HOSTILE), [], [], "m", 1, T0)
        self.fid = requests_store.add_finding(self.file_conn, rid, "owner", "n", "2026-11-20T10:00:00Z")
        self.file_conn.commit()
        self.app = web.create_app(port=PORT, token=TOKEN)

    def api(self, method, path, **kwargs):
        headers = {"X-Recall-Token": TOKEN, **kwargs.pop("headers", {})}
        return call(self.app, method, path, headers=headers, **kwargs)

    def test_download_needs_the_token(self):
        status, _h, _t = call(self.app, "GET", "/api/findings/export", query="format=md")
        self.assertEqual(status, 403)

    def test_download_is_an_attachment_with_the_right_type_and_escaped_html(self):
        status, headers, text = self.api("GET", "/api/findings/export", query="format=html")
        self.assertEqual(status, 200)
        lowered = {k.lower(): v for k, v in dict(headers).items()}
        self.assertIn("attachment", lowered["content-disposition"])
        self.assertTrue(lowered["content-type"].startswith("text/html"))
        self.assertEqual(lowered["x-content-type-options"], "nosniff")
        self.assertNotIn("<script>alert", text)
        status, _h, text = self.api("GET", "/api/findings/export", query="format=md")
        self.assertEqual(status, 200)
        self.assertIn(exporter.MARKER, text)

    def test_a_bad_format_is_refused(self):
        status, _h, _t = self.api("GET", "/api/findings/export", query="format=pdf")
        self.assertEqual(status, 422)

    def test_list_edit_note_and_delete(self):
        status, _h, text = self.api("GET", "/api/findings")
        self.assertEqual((status, json.loads(text)["findings"][0]["finding_id"]), (200, self.fid))
        status, _h, _t = self.api("PUT", f"/api/findings/{self.fid}", body={"note": "changed"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.api("GET", "/api/findings")[2])["findings"][0]["note"], "changed")
        self.assertEqual(self.api("DELETE", f"/api/findings/{self.fid}")[0], 200)
        self.assertEqual(json.loads(self.api("GET", "/api/findings")[2])["findings"], [])
        self.assertEqual(self.api("DELETE", f"/api/findings/{self.fid}")[0], 400)


if __name__ == "__main__":
    unittest.main()
