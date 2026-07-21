"""Tests for the toolkit scripts' pure/offline logic.

conftest.py puts the plugin `scripts/` dir on sys.path before collection, so
these local modules import at the top like any other package.
"""
import json
import os
import subprocess
import sys

# Local modules from plugins/youtube-toolkit/scripts (path set by conftest.py).
import fetch_transcript as ft
import pytest
import screenshot_pdf as sp
import video_frames as vf

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "plugins", "youtube-toolkit", "scripts")


# --- fetch_transcript ------------------------------------------------------
@pytest.mark.parametrize("url,expected", [
    ("https://youtu.be/lhWP7kkylTE?si=abc", "lhWP7kkylTE"),
    ("https://www.youtube.com/watch?v=lhWP7kkylTE", "lhWP7kkylTE"),
    ("https://www.youtube.com/shorts/lhWP7kkylTE", "lhWP7kkylTE"),
    ("https://www.youtube.com/embed/lhWP7kkylTE", "lhWP7kkylTE"),
    ("lhWP7kkylTE", "lhWP7kkylTE"),
])
def test_video_id(url, expected):
    assert ft.video_id(url) == expected


def test_parse_json3(tmp_path):
    payload = {"events": [
        {"tStartMs": 0, "segs": [{"utf8": "hello "}, {"utf8": "world"}]},
        {"tStartMs": 61000, "segs": [{"utf8": "later"}]},
        {"tStartMs": 5000, "segs": [{"utf8": "  "}]},  # whitespace-only -> dropped
    ]}
    p = tmp_path / "c.json3"
    p.write_text(json.dumps(payload), encoding="utf-8")
    plain = ft.parse_json3(str(p), timestamps=False)
    assert plain.splitlines() == ["hello world", "later"]
    stamped = ft.parse_json3(str(p), timestamps=True)
    assert stamped.splitlines()[0] == "[00:00:00] hello world"
    assert stamped.splitlines()[1] == "[00:01:01] later"


# --- screenshot_pdf --------------------------------------------------------
@pytest.mark.parametrize("ts,secs", [("0", 0), ("6:00", 360), ("1:01:00", 3660), ("32:30", 1950)])
def test_to_seconds(ts, secs):
    assert sp.to_seconds(ts) == secs


def test_load_claims_from_timestamps():
    class Args:
        claims = None
        timestamps = "0,6:00,32:30"
    claims = sp.load_claims(Args())
    assert [c["timestamp"] for c in claims] == ["0", "6:00", "32:30"]
    assert all(c["section"] == "Recap" and c["text"] == "" for c in claims)


# --- video_frames ----------------------------------------------------------
def test_parse_ts():
    assert vf.parse_ts("90") == 90
    assert vf.parse_ts("1:30") == 90
    assert vf.parse_ts("1:00:00") == 3600


# --- process_transcript (via CLI) -----------------------------------------
def test_process_transcript_dedups_rolling_captions():
    raw = ("[00:00:01] hello there\n"
           "[00:00:01] hello there world\n"
           "[00:00:03] world this is a test\n")
    proc = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "process_transcript.py"), "--mode", "clean"],
        input=raw, capture_output=True, text=True)
    assert proc.returncode == 0
    # rolling duplication collapses to a single clean line
    assert "hello there world this is a test" in proc.stdout


# --- build_pdf -------------------------------------------------------------
def test_build_pdf_no_images(tmp_path):
    pytest.importorskip("reportlab")
    import build_pdf
    out = tmp_path / "out.pdf"
    items = [{"timestamp": "00:00", "section": "Intro", "text": "Cold open."},
             {"timestamp": "6:00", "section": "Topic", "text": "Main."}]
    path = build_pdf.build_pdf(items, str(out), subtitle="test")
    assert os.path.isfile(path) and os.path.getsize(path) > 500
