# youtube-toolkit MCP server

A thin [MCP](https://modelcontextprotocol.io) server that wraps the
`youtube-toolkit` plugin scripts and exposes two tools:

- **`fetch_transcript(url, lang="en", timestamps=true)`** → `scripts/fetch_transcript.py`
- **`generate_timestamped_pdf(video_url, timestamps_and_claims, output_pdf_name)`** → `scripts/screenshot_pdf.py`

Why an MCP server: it holds the **access credentials in its launch environment**,
so cookies/proxy/po_token settings apply to every call and **never appear at the
call site** (the model just calls the tool with a URL and, for the PDF, a list of
`{timestamp, section?, text?}`).

## Install
```bash
pip install -r mcp-server/requirements.txt
# for screenshots you also need a JS runtime + the access stack — see
# ../plugins/youtube-toolkit/resources/unblocking-youtube.md
```

## Configure access (on the server's env)
Set whatever you need where the server launches — not in the repo:
- `YT_COOKIES` (`YT_TRANSCRIPT_COOKIES`) — path to a Netscape `cookies.txt` (clears 429)
- `YT_PROXY` (`YT_TRANSCRIPT_PROXY`) — residential proxy URL
- `YT_NO_CHECK_CERTS` — disable cert checks behind a TLS-intercepting proxy
- `YT_POT_PROVIDER_HOME` — built bgutil server dir (auto-start the po_token provider)

## Register in Claude Code
```bash
claude mcp add youtube-toolkit \
  --env YT_COOKIES=/secure/path/cookies.txt \
  -- python3 /abs/path/to/mcp-server/youtube_transcript_server.py
```

Or via a project `.mcp.json`:
```json
{
  "mcpServers": {
    "youtube-toolkit": {
      "command": "python3",
      "args": ["mcp-server/youtube_transcript_server.py"],
      "env": { "YT_COOKIES": "/secure/path/cookies.txt" }
    }
  }
}
```

## Notes
- Secrets live only in the launch env / an external `cookies.txt` (git-ignored) — never committed.
- `TOOLKIT_SCRIPTS` overrides the location of the plugin `scripts/` dir if needed.
- Exit-code meanings surfaced as tool errors: `2` no captions · `3` rate-limited /
  no formats (set cookies/proxy) · `4` yt-dlp/ffmpeg missing · `5` network/extraction error.
- This is a minimal stdio scaffold, not a published package.
