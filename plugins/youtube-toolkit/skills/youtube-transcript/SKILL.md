---
name: youtube-transcript
description: Fetch the spoken transcript (captions) of a YouTube video or Short. Use when the user gives a YouTube URL or video ID and wants the transcript, captions, spoken-content summary, or quotes from a video. Trigger with phrases like "get the transcript", "transcribe this YouTube video", or "what does this video say".
---

# YouTube Transcript

Fetch the spoken transcript (captions) from a YouTube video or Short. Delegates
to yt-dlp through the plugin's shared access layer, so it auto-wires a JS
runtime + EJS solver, cookies/proxy, and an optional po_token provider.

## How to run
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch_transcript.py \
    <url-or-id> [--timestamps] [--lang en] [--proxy URL] [--cookies cookies.txt] \
    [--no-check-certs] [--out file.txt]
```

## Requirements
- `yt-dlp` (>= 2025.x): `pip install yt-dlp`
- Recommended: `deno` JS runtime — required for the EJS challenge solver on
  recent yt-dlp (captions can still fail without it).

## Access / credentials
From a datacenter IP YouTube bot-gates or 429s. Configure once; the script
resolves **flag > env var > auto-detected file** and never prints secret values:

| Env var | Effect |
|---|---|
| `YT_COOKIES` (`YT_TRANSCRIPT_COOKIES`) | Netscape `cookies.txt` — clears 429 |
| `YT_PROXY` (`YT_TRANSCRIPT_PROXY` / `HTTPS_PROXY`) | residential egress |
| `YT_NO_CHECK_CERTS` | disable cert checks behind a TLS-intercepting proxy |

A `cookies.txt` in `${CLAUDE_PLUGIN_ROOT}` or beside the scripts is auto-detected.
**Full setup — deno + EJS + po_token provider + cookies — is in
[`resources/unblocking-youtube.md`](../../resources/unblocking-youtube.md).**

## Why naive approaches break
1. Parsing `ytInitialPlayerResponse` from HTML returns empty `captionTracks`. Never do this.
2. Default web/android clients return zero tracks. The script forces
   `player_client=android_vr,tv,web`.
3. `timedtext` 429s datacenter IPs. The script retries with backoff; for hard
   blocks add cookies or a proxy.
4. Recent yt-dlp needs the **EJS solver** for the n-challenge — deno alone is no
   longer enough. The access layer adds `--remote-components ejs:npm` when deno
   is present.

## Exit codes
`0` ok · `2` no captions · `3` rate-limited (add cookies/proxy) · `4` yt-dlp missing · `5` network error.

## Follow-up
To clean/segment the result, use the **transcript-processor** skill. To capture
screenshots at moments in the transcript, use the **video-screenshots** skill.
