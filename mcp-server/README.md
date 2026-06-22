# youtube-transcript MCP server

A thin [MCP](https://modelcontextprotocol.io) server that wraps the fetch plugin and
exposes one tool, **`fetch_transcript(url, lang="en", timestamps=true)`**. It delegates to
`plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py`.

Why an MCP server: it holds the **credentials in its launch environment**, so proxy/cookies
are applied to every call and **never appear at the call site** (the model just calls the
tool with a URL).

## Install
```bash
pip install -r mcp-server/requirements.txt
```

## Configure credentials (on the server's env)
Set whichever you need where the server is launched — not in the repo:
- `YT_TRANSCRIPT_PROXY` (or `HTTPS_PROXY`) — residential proxy URL
- `YT_TRANSCRIPT_COOKIES` — path to a Netscape `cookies.txt`
- `YT_TRANSCRIPT_NO_CHECK_CERTS=1` — disable cert checks behind a TLS-intercepting proxy

## Register in Claude Code
```bash
claude mcp add youtube-transcript \
  --env YT_TRANSCRIPT_COOKIES=/secure/path/cookies.txt \
  --env YT_TRANSCRIPT_NO_CHECK_CERTS=1 \
  -- python3 /abs/path/to/mcp-server/youtube_transcript_server.py
```

Or via a project `.mcp.json`:
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "python3",
      "args": ["mcp-server/youtube_transcript_server.py"],
      "env": {
        "YT_TRANSCRIPT_COOKIES": "/secure/path/cookies.txt",
        "YT_TRANSCRIPT_NO_CHECK_CERTS": "1"
      }
    }
  }
}
```

## Notes
- Secrets live only in the launch env / an external `cookies.txt` (git-ignored) — never
  committed.
- Exit-code meanings (surfaced as tool errors): `2` no captions · `3` rate-limited (set a
  proxy/cookies) · `4` yt-dlp missing · `5` network/DNS/cert error.
- This is a minimal stdio scaffold (one tool), not a published package.
