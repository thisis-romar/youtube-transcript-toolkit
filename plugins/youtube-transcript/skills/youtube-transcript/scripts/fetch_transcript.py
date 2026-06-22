#!/usr/bin/env python3
"""
Fetch a YouTube transcript reliably.

Why this exists: scraping ytInitialPlayerResponse from watch-page HTML now
returns zero caption tracks (YouTube strips them from naive player responses),
and the timedtext endpoint rate-limits datacenter IPs with HTTP 429. This script
delegates extraction to yt-dlp (which tracks YouTube's client changes), forces a
client that still exposes captions, parses json3, and backs off on 429.

Usage:
    python3 fetch_transcript.py <url-or-id> [options]

Options:
    --lang LANG        Preferred language prefix (default: en). Matches en, en-orig, en-US...
    --timestamps       Emit [HH:MM:SS] prefixes.
    --proxy URL        Route through a proxy (e.g. http://user:pass@host:port). Bypasses 429.
    --cookies FILE     Netscape cookies.txt for age/region/PO-token gated videos.
    --no-check-certs   Pass --no-check-certificates (needed behind TLS-intercepting proxies).
    --out FILE         Write to FILE instead of stdout.

Exit codes: 0 ok | 2 no captions | 3 rate-limited after retries | 4 yt-dlp missing
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time

JS_RUNTIME_HINT = "deno"  # install for clean extraction: `curl -fsSL https://deno.land/install.sh | sh`


def video_id(s: str) -> str:
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else s.strip()


def run_ytdlp(vid, lang, tmp, proxy, cookies, no_check_certs):
    """Return path to a downloaded .json3 sub file, or None."""
    if not shutil.which("yt-dlp"):
        print("yt-dlp not installed: pip install yt-dlp", file=sys.stderr)
        sys.exit(4)
    url = f"https://www.youtube.com/watch?v={vid}"
    cmd = [
        "yt-dlp", "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", f"{lang}.*,{lang}",
        "--sub-format", "json3",
        # Force clients that still expose caption tracks. android_vr / tv work
        # when the default web/android clients return zero tracks.
        "--extractor-args", "youtube:player_client=android_vr,tv,web",
        "-o", os.path.join(tmp, "%(id)s.%(ext)s"),
        "--retries", "2", "--socket-timeout", "30",
    ]
    if proxy:          cmd += ["--proxy", proxy]
    if cookies:        cmd += ["--cookies", cookies]
    if no_check_certs: cmd += ["--no-check-certificates"]
    cmd.append(url)

    backoff = 5
    for attempt in range(1, 5):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        err = proc.stderr
        # Find any json3 that landed.
        for f in os.listdir(tmp):
            if f.endswith(".json3"):
                return os.path.join(tmp, f)
        if "429" in err or "Too Many Requests" in err:
            if attempt == 4:
                print("Rate-limited (429) after retries. Use --proxy or --cookies, "
                      "or run from a non-datacenter IP.", file=sys.stderr)
                sys.exit(3)
            print(f"[429] backing off {backoff}s (attempt {attempt}/3)", file=sys.stderr)
            time.sleep(backoff); backoff *= 2; continue
        if "No supported JavaScript runtime" in err:
            print(f"Note: no JS runtime found; install {JS_RUNTIME_HINT} for robust "
                  "extraction. Continuing.", file=sys.stderr)
        # No subs and not a 429 -> give yt-dlp's reason once and stop.
        if attempt == 1 and ("no subtitles" in err.lower() or "available" not in err.lower()):
            sys.stderr.write(err)
        break
    return None


def parse_json3(path, timestamps=False):
    j = json.load(open(path, encoding="utf-8"))
    lines = []
    for e in j.get("events", []):
        if "segs" not in e:
            continue
        text = "".join(s.get("utf8", "") for s in e["segs"]).replace("\n", " ").strip()
        if not text:
            continue
        if timestamps:
            ms = e.get("tStartMs", 0)
            h, rem = divmod(ms // 1000, 3600)
            m, s = divmod(rem, 60)
            lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--timestamps", action="store_true")
    ap.add_argument("--proxy")
    ap.add_argument("--cookies")
    ap.add_argument("--no-check-certs", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    vid = video_id(a.url)
    with tempfile.TemporaryDirectory() as tmp:
        sub = run_ytdlp(vid, a.lang, tmp, a.proxy, a.cookies, a.no_check_certs)
        if not sub:
            print(f"No captions retrieved for {vid}.", file=sys.stderr)
            sys.exit(2)
        out = parse_json3(sub, a.timestamps)

    if a.out:
        open(a.out, "w", encoding="utf-8").write(out + "\n")
        print(f"Wrote {a.out} ({len(out.splitlines())} lines)", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
