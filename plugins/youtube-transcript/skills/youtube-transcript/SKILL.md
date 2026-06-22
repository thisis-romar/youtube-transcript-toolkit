---
name: youtube-transcript
description: Fetch the spoken transcript (captions) of a YouTube video or Short. Use when the user gives a YouTube URL or video ID and wants the transcript, captions, spoken-content summary, or quotes from a video. Trigger with phrases like "get the transcript", "transcribe this YouTube video", or "what does this video say".
---

# YouTube Transcript

Fetch the spoken transcript (captions) from a YouTube video or Short.

## How to run
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-transcript/scripts/fetch_transcript.py \
    <url-or-id> [--timestamps] [--lang en] [--proxy URL] [--cookies cookies.txt] \
    [--no-check-certs] [--out file.txt]
```

## Requirements
- `yt-dlp` (>= 2025.x): `pip install yt-dlp`
- Recommended: `deno` JS runtime for clean extraction.
- Behind a TLS-intercepting proxy, pass `--no-check-certs`.

## Why naive approaches break
1. Parsing `ytInitialPlayerResponse` from HTML returns empty `captionTracks`. Never do this.
2. Default web/android InnerTube clients return zero tracks. Script forces
   `player_client=android_vr,tv,web` via `--extractor-args`.
3. `timedtext` endpoint returns HTTP 429 from datacenter IPs. Script retries
   with exponential backoff; for hard blocks use `--proxy` or `--cookies`.

## Exit codes
`0` success · `2` no captions · `3` rate-limited (use `--proxy`/`--cookies`) · `4` yt-dlp missing.
