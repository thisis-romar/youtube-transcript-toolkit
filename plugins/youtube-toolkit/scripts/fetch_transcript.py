#!/usr/bin/env python3
"""Fetch a YouTube transcript reliably.

Scraping ytInitialPlayerResponse from watch-page HTML returns zero caption
tracks, and the timedtext endpoint 429s datacenter IPs. This delegates to
yt-dlp and routes every request through the shared access layer
(`ytdlp_access`), which auto-wires a JS runtime + EJS solver, cookies/proxy,
and an optional po_token provider. Captions come from the android_vr/tv/web
clients, which still expose tracks when the default client returns none.

Usage:
    python3 fetch_transcript.py <url-or-id> [options]

Options:
    --lang LANG        Preferred language prefix (default: en). Matches en, en-orig, en-US...
    --timestamps       Emit [HH:MM:SS] prefixes.
    --proxy URL        Route through a proxy. Overrides $YT_PROXY.
    --cookies FILE     Netscape cookies.txt. Overrides $YT_COOKIES.
    --no-check-certs   Pass --no-check-certificates (TLS-intercepting proxies).
    --out FILE         Write to FILE instead of stdout.
    --raw-out FILE     Also copy the downloaded json3 caption payload to FILE.

See resources/unblocking-youtube.md for the credential/env setup.
Exit codes: 0 ok | 2 no captions | 3 rate-limited after retries | 4 yt-dlp missing | 5 network error
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ytdlp_access as access  # noqa: E402


def is_network_error(stderr: str) -> bool:
    s = stderr.lower()
    indicators = (
        "network is unreachable", "name or service not known",
        "temporary failure in name resolution", "unable to download webpage",
        "unable to download api page", "urlopen error", "proxyerror",
        "proxy error", "tunnel connection failed", "connection refused",
        "connection reset", "timed out", "timeout", "ssl:",
        "certificate verify failed",
    )
    return any(i in s for i in indicators)


def video_id(s: str) -> str:
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", s)
    return m.group(1) if m else s.strip()


def run_ytdlp(vid, lang, tmp, proxy, cookies, no_check_certs):
    """Return path to a downloaded .json3 sub file, or None."""
    access.require_ytdlp()
    url = f"https://www.youtube.com/watch?v={vid}"
    cmd = access.ytdlp_cli() + [
        "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", f"{lang}.*,{lang}",
        "--sub-format", "json3",
        "-o", os.path.join(tmp, "%(id)s.%(ext)s"),
        "--retries", "2", "--socket-timeout", "30",
    ]
    # Caption tracks surface on android_vr/tv/web; EJS+cookies+proxy auto-added.
    cmd += access.common_cli_flags(proxy, cookies, no_check_certs,
                                   player_client="android_vr,tv,web")
    cmd.append(url)

    backoff = 5
    for attempt in range(1, 5):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        err = proc.stderr
        for f in os.listdir(tmp):
            if f.endswith(".json3"):
                return os.path.join(tmp, f)
        if "429" in err or "Too Many Requests" in err:
            if attempt == 4:
                print("Rate-limited (429) after retries. Add cookies ($YT_COOKIES) or a "
                      "--proxy, or run from a non-datacenter IP. "
                      "See resources/unblocking-youtube.md.", file=sys.stderr)
                sys.exit(3)
            print(f"[429] backing off {backoff}s (attempt {attempt}/3)", file=sys.stderr)
            time.sleep(backoff); backoff *= 2; continue
        if is_network_error(err):
            sys.stderr.write(err)
            print("Network error before captions could be checked. Check DNS, egress, "
                  "proxy, and certificate settings.", file=sys.stderr)
            sys.exit(5)
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
    ap.add_argument("--raw-out", help="Copy downloaded json3 captions to FILE")
    a = ap.parse_args()

    proxy, cookies, no_check_certs = access.resolve_credentials(
        a.proxy, a.cookies, a.no_check_certs)

    vid = video_id(a.url)
    with tempfile.TemporaryDirectory() as tmp:
        sub = run_ytdlp(vid, a.lang, tmp, proxy, cookies, no_check_certs)
        if not sub:
            print(f"No captions retrieved for {vid}.", file=sys.stderr)
            sys.exit(2)
        out = parse_json3(sub, a.timestamps)
        if a.raw_out:
            shutil.copyfile(sub, a.raw_out)

    if a.out:
        open(a.out, "w", encoding="utf-8").write(out + "\n")
        print(f"Wrote {a.out} ({len(out.splitlines())} lines)", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
