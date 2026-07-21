#!/usr/bin/env python3
"""Build youtube_mcp_plugin.zip — a distributable MCP screenshot plugin.

This packages the SAME engine the youtube-toolkit plugin and MCP server use
(no divergent copy): the shared access layer plus the download → frame →
PDF pipeline, wrapped in a thin FastMCP server that exposes
`generate_timestamped_pdf`. Run from the repo:

    python3 build_zip.py [output.zip]
"""
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(REPO, "plugins", "youtube-toolkit", "scripts")
RESOURCES = os.path.join(REPO, "plugins", "youtube-toolkit", "resources")

# Shared engine files copied verbatim into the zip (single source of truth).
BUNDLED = ["ytdlp_access.py", "video_frames.py", "build_pdf.py", "screenshot_pdf.py"]

# Thin FastMCP wrapper generated into the zip.
MCP_SERVER = '''import json
import os
import subprocess
import sys
import tempfile

from fastmcp import FastMCP

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(HERE, "screenshot_pdf.py")

mcp = FastMCP("YouTube Video Timestamp & PDF Generator")


@mcp.tool()
def generate_timestamped_pdf(
    video_url: str,
    timestamps_and_claims: list[dict],
    output_pdf_name: str = "recap_with_screenshots.pdf",
) -> str:
    """Capture screenshots at timestamps and compile a recap PDF.

    timestamps_and_claims: list of {timestamp, section?, text?} with timestamp
    as "SS", "MM:SS", or "HH:MM:SS". Access settings (cookies/proxy/EJS/po_token)
    are read from the environment; see unblocking-youtube.md.
    """
    with tempfile.TemporaryDirectory() as tmp:
        claims = os.path.join(tmp, "claims.json")
        with open(claims, "w", encoding="utf-8") as f:
            json.dump(timestamps_and_claims, f)
        cmd = [sys.executable, SHOT, video_url, "--claims", claims,
               "-o", output_pdf_name, "--work-dir", os.path.join(tmp, "work")]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
        if proc.returncode == 0:
            return proc.stdout.strip()
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        return f"Error (exit {proc.returncode}): " + "\\n".join(tail)


if __name__ == "__main__":
    mcp.run()
'''

REQUIREMENTS = "fastmcp\nyt-dlp\nreportlab\nimageio-ffmpeg\n"

CONFIG = '''{
  "mcpServers": {
    "youtube-pdf-tool": {
      "command": "python",
      "args": ["path/to/mcp_server.py"],
      "env": {
        "YT_COOKIES": "/secure/path/cookies.txt"
      }
    }
  }
}
'''

README = '''# YouTube Video Timestamp & PDF Generator (MCP)

Captures frames from a YouTube video at given timestamps and compiles a PDF with
the screenshots and recap text. Exposes one tool: `generate_timestamped_pdf`.

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python mcp_server.py
```

## Access / credentials
YouTube gates video bytes behind a po_token (403/DRM), an n-challenge, and a
datacenter-IP 429. This packages the auto-wiring access layer; you supply:
- `deno` on PATH (JS runtime) — enables the EJS challenge solver,
- a `cookies.txt` via `YT_COOKIES` (or a residential `YT_PROXY`),
- optionally a bgutil po_token provider via `YT_POT_PROVIDER_HOME`.

See `unblocking-youtube.md` for the full setup.

## Claude Desktop
Add `claude_desktop_config.json` to your config, updating the path and setting
`YT_COOKIES` in its `env`.
'''


def create_zip_package(output_zip: str = "youtube_mcp_plugin.zip") -> str:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for name in BUNDLED:
            zipf.write(os.path.join(SCRIPTS, name), name)
            print(f"Added {name} (from toolkit scripts)")
        zipf.writestr("mcp_server.py", MCP_SERVER)
        zipf.writestr("requirements.txt", REQUIREMENTS)
        zipf.writestr("claude_desktop_config.json", CONFIG)
        zipf.writestr("README.md", README)
        zipf.write(os.path.join(RESOURCES, "unblocking-youtube.md"), "unblocking-youtube.md")
        for extra in ("mcp_server.py", "requirements.txt", "claude_desktop_config.json",
                      "README.md", "unblocking-youtube.md"):
            print(f"Added {extra}")
    abspath = os.path.abspath(output_zip)
    print(f"\nCreated successfully: {abspath}")
    return abspath


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "youtube_mcp_plugin.zip"
    create_zip_package(target)
