#!/usr/bin/env python3
"""
MCP server wrapping the youtube-transcript fetch plugin.

Exposes a single tool, `fetch_transcript`, that delegates to the plugin's
`fetch_transcript.py`. Credentials (proxy / cookies / cert handling) are NOT
parameters — they are read from the server's launch environment by the
underlying script, so secrets never appear at the call site:

    YT_TRANSCRIPT_PROXY            proxy URL (or HTTPS_PROXY)
    YT_TRANSCRIPT_COOKIES          path to a cookies.txt
    YT_TRANSCRIPT_NO_CHECK_CERTS   truthy to disable cert checks

Run:  python3 youtube_transcript_server.py        (stdio transport)
Register in Claude Code with these env vars set on the server entry.
"""
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

# Locate the plugin fetch script relative to this file (override with $FETCH_SCRIPT).
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SCRIPT = os.path.normpath(os.path.join(
    _HERE, "..", "plugins", "youtube-transcript", "skills",
    "youtube-transcript", "scripts", "fetch_transcript.py"))
FETCH_SCRIPT = os.environ.get("FETCH_SCRIPT", _DEFAULT_SCRIPT)

_EXIT_MEANING = {
    2: "no captions available for this video",
    3: "rate-limited (HTTP 429) from this IP — set YT_TRANSCRIPT_PROXY or YT_TRANSCRIPT_COOKIES",
    4: "yt-dlp is not installed (pip install yt-dlp)",
    5: "network error before captions could be checked — check DNS/egress/proxy/certs",
}

mcp = FastMCP("youtube-transcript")


@mcp.tool()
def fetch_transcript(url: str, lang: str = "en", timestamps: bool = True) -> str:
    """Fetch the spoken transcript (captions) of a YouTube video or Short.

    Args:
        url: YouTube URL or 11-character video ID.
        lang: Caption language prefix (default "en").
        timestamps: Prefix each line with [HH:MM:SS] (default True).

    Returns the transcript text. Proxy/cookies/cert settings come from the
    server's environment, not from this call.
    """
    cmd = [sys.executable, FETCH_SCRIPT, url, "--lang", lang]
    if timestamps:
        cmd.append("--timestamps")
    # Inherit os.environ so the script picks up YT_TRANSCRIPT_* credentials.
    proc = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    if proc.returncode == 0:
        return proc.stdout.strip() or "(empty transcript)"
    meaning = _EXIT_MEANING.get(proc.returncode, "fetch failed")
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    raise RuntimeError(f"exit {proc.returncode}: {meaning}\n" + "\n".join(tail))


if __name__ == "__main__":
    mcp.run()
