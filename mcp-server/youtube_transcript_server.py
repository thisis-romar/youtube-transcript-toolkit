#!/usr/bin/env python3
"""
MCP server wrapping the youtube-toolkit plugin.

Exposes two tools that delegate to the plugin's shared scripts:
  - `fetch_transcript`          -> scripts/fetch_transcript.py
  - `generate_timestamped_pdf`  -> scripts/screenshot_pdf.py

Credentials and access settings (cookies / proxy / po_token provider / EJS) are
NOT parameters — they are read from the server's launch environment by the
shared access layer, so secrets never appear at the call site:

    YT_COOKIES / YT_TRANSCRIPT_COOKIES   path to a cookies.txt
    YT_PROXY   / YT_TRANSCRIPT_PROXY      proxy URL (or HTTPS_PROXY)
    YT_NO_CHECK_CERTS                     truthy to disable cert checks
    YT_POT_PROVIDER_HOME                  built bgutil server dir (auto-start)
See plugins/youtube-toolkit/resources/unblocking-youtube.md.

Run:  python3 youtube_transcript_server.py        (stdio transport)
"""
import json
import os
import subprocess
import sys
import tempfile

from mcp.server.fastmcp import FastMCP

# Locate the plugin scripts relative to this file (override with $TOOLKIT_SCRIPTS).
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.environ.get("TOOLKIT_SCRIPTS", os.path.normpath(
    os.path.join(_HERE, "..", "plugins", "youtube-toolkit", "scripts")))
FETCH_SCRIPT = os.path.join(_SCRIPTS, "fetch_transcript.py")
SHOT_SCRIPT = os.path.join(_SCRIPTS, "screenshot_pdf.py")

_EXIT_MEANING = {
    2: "no captions available for this video",
    3: "rate-limited / no formats (HTTP 429) — set YT_COOKIES or YT_PROXY",
    4: "yt-dlp or ffmpeg is not installed",
    5: "network or extraction error — check DNS/egress/proxy/certs",
}

mcp = FastMCP("youtube-toolkit")


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    if proc.returncode == 0:
        return proc.stdout.strip()
    meaning = _EXIT_MEANING.get(proc.returncode, "command failed")
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    raise RuntimeError(f"exit {proc.returncode}: {meaning}\n" + "\n".join(tail))


@mcp.tool()
def fetch_transcript(url: str, lang: str = "en", timestamps: bool = True) -> str:
    """Fetch the spoken transcript (captions) of a YouTube video or Short.

    Args:
        url: YouTube URL or 11-character video ID.
        lang: Caption language prefix (default "en").
        timestamps: Prefix each line with [HH:MM:SS] (default True).

    Access settings come from the server environment, not this call.
    """
    cmd = [sys.executable, FETCH_SCRIPT, url, "--lang", lang]
    if timestamps:
        cmd.append("--timestamps")
    return _run(cmd) or "(empty transcript)"


@mcp.tool()
def generate_timestamped_pdf(
    video_url: str,
    timestamps_and_claims: list[dict],
    output_pdf_name: str = "recap_with_screenshots.pdf",
) -> str:
    """Capture screenshots at timestamps and compile a recap PDF.

    Args:
        video_url: YouTube URL or video ID.
        timestamps_and_claims: list of {timestamp, section?, text?} where
            timestamp is "SS", "MM:SS", or "HH:MM:SS".
        output_pdf_name: destination PDF path.

    Downloads the video once (auto-wired access: cookies/EJS/po_token), extracts
    a frame per timestamp locally, and renders the styled recap PDF. Access
    settings come from the server environment.
    """
    with tempfile.TemporaryDirectory() as tmp:
        claims_path = os.path.join(tmp, "claims.json")
        with open(claims_path, "w", encoding="utf-8") as f:
            json.dump(timestamps_and_claims, f)
        cmd = [sys.executable, SHOT_SCRIPT, video_url,
               "--claims", claims_path, "-o", output_pdf_name,
               "--work-dir", os.path.join(tmp, "work")]
        return _run(cmd)


if __name__ == "__main__":
    mcp.run()
