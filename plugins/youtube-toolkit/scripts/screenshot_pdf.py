#!/usr/bin/env python3
"""End-to-end: YouTube URL + timestamped claims -> screenshot recap PDF.

This is the single entry point behind all three surfaces of the screenshot
capability (the video-screenshots skill, the MCP `generate_timestamped_pdf`
tool, and the build_zip package). It composes the shared pieces:

    video_frames.py  -> download + extract frames (auto-wired access)
    build_pdf.py     -> render the recap PDF

Two ways to supply the moments:
  --claims claims.json   JSON list of {timestamp, section?, text?} (timestamp as
                         SS | MM:SS | HH:MM:SS). Full control over captions/sections.
  --timestamps LIST      Comma list of marks; captions default to the timestamp.

Usage:
    python3 screenshot_pdf.py <url> --claims claims.json -o recap.pdf
    python3 screenshot_pdf.py <url> --timestamps 0,6:00,32:30 -o recap.pdf

Exit codes mirror video_frames.py (3 = blocked IP, 4 = missing tool, 5 = other).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pdf as pdf  # noqa: E402


def load_claims(args):
    if args.claims:
        claims = json.load(open(args.claims, encoding="utf-8"))
    else:
        claims = [{"timestamp": t.strip()} for t in args.timestamps.split(",") if t.strip()]
    for c in claims:
        c.setdefault("section", "Recap")
        c.setdefault("text", "")
    return claims


def to_seconds(s: str) -> int:
    parts = [int(p) for p in str(s).strip().split(":")]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--claims", help="JSON list of {timestamp, section?, text?}")
    g.add_argument("--timestamps", help="Comma list of SS|MM:SS|HH:MM:SS marks")
    ap.add_argument("-o", "--out", default="recap_with_screenshots.pdf")
    ap.add_argument("--work-dir", default="_screenshot_work")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--title", default="YouTube Video Timestamped Recap")
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--proxy")
    ap.add_argument("--cookies")
    ap.add_argument("--no-check-certs", action="store_true")
    a = ap.parse_args()

    claims = load_claims(a)
    os.makedirs(a.work_dir, exist_ok=True)
    ts_list = ",".join(str(to_seconds(c["timestamp"])) for c in claims)

    cmd = [sys.executable, os.path.join(HERE, "video_frames.py"), a.url,
           "--timestamps", ts_list, "--out-dir", a.work_dir, "--height", str(a.height)]
    if a.proxy:          cmd += ["--proxy", a.proxy]
    if a.cookies:        cmd += ["--cookies", a.cookies]
    if a.no_check_certs: cmd += ["--no-check-certs"]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        sys.exit(proc.returncode)

    # Map captured frames (seconds -> path) back onto the claims in order.
    by_sec = {}
    for line in proc.stdout.splitlines():
        if "\t" in line:
            sec, path = line.split("\t", 1)
            by_sec[int(sec)] = path
    for c in claims:
        c["image_path"] = by_sec.get(to_seconds(c["timestamp"]))

    path = pdf.build_pdf(claims, a.out, a.title, a.subtitle)
    n = sum(1 for c in claims if c.get("image_path"))
    print(f"Successfully created PDF recap ({n}/{len(claims)} frames) at: {path}")


if __name__ == "__main__":
    main()
