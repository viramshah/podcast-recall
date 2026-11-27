"""Writing the findings into one Apple Notes note (Week 5, decision D25).

macOS only, local only. One note named "Podcast Recall findings" is created on the first export and
rewritten in place after that, so a re-export never makes a second note. The note's text goes to
AppleScript as an argument, never pasted into the script, so quote text cannot change the script.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence

from podcast_recall.errors import ConfigError
from podcast_recall.exporter import TITLE

SCRIPT = """
on run argv
    set noteName to item 1 of argv
    set noteBody to item 2 of argv
    tell application "Notes"
        set found to every note whose name is noteName
        if (count of found) > 0 then
            set body of item 1 of found to noteBody
            return "updated"
        else
            make new note with properties {body:noteBody}
            return "created"
        end if
    end tell
end run
"""

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), capture_output=True, text=True, timeout=120, check=False)


def write_note(body_html: str, runner: Runner = _run, platform: str | None = None) -> str:
    """Create or update the findings note. Returns "created" or "updated"."""
    if (platform or sys.platform) != "darwin":
        raise ConfigError("Apple Notes export only works on a Mac.")
    result = runner(["osascript", "-e", SCRIPT, TITLE, body_html])
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()[-1:] or ["no details"]
        raise ConfigError(
            "Apple Notes did not accept the export (" + detail[0][:160] + "). "
            "Allow your terminal to control Notes in System Settings, Privacy & Security, Automation."
        )
    return (result.stdout or "").strip() or "updated"
