---
name: video-screenshots
description: Capture screenshots from a YouTube video at specific timestamps and compile them, with recap text, into a styled PDF. Use when the user wants frames/screenshots/stills from a video, a visual recap, a "screenshot at each timestamp", or a PDF of key moments from a YouTube URL. Trigger with phrases like "grab screenshots from this video", "make a PDF of key moments", or "capture frames at these timestamps".
---

# Video Screenshots → Recap PDF

Download a YouTube video and extract frames at exact timestamps, then compile
them with recap text into a styled PDF. Uses the plugin's shared access layer,
so it survives the po_token/DRM (403), n-challenge, and datacenter-IP (429)
walls — **frame capture needs all three cleared**, so read
[`resources/unblocking-youtube.md`](../../resources/unblocking-youtube.md) first
(cookies are almost always required).

## How to run

**Simple — just timestamps** (captions default to the timestamp label):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/screenshot_pdf.py <url> \
    --timestamps 0,6:00,7:30,11:30,32:30,44:00 -o recap.pdf
```

**Full control — a claims file** with sections and captions:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/screenshot_pdf.py <url> \
    --claims claims.json -o recap.pdf --subtitle "Title — Channel · youtu.be/ID"
```
`claims.json` is a list of `{timestamp, section, text}` (timestamp = `SS`,
`MM:SS`, or `HH:MM:SS`):
```json
[
  {"timestamp": "00:00",   "section": "Intro",   "text": "Cold open."},
  {"timestamp": "6:00",    "section": "Topic",   "text": "Main subject begins."},
  {"timestamp": "1:01:00", "section": "Outro",   "text": "Wrap-up."}
]
```

## Recommended workflow for Claude
1. Fetch the transcript first (**youtube-transcript** skill) to pick meaningful
   moments — topic shifts, on-screen artifacts, deictic cues ("look here").
2. Build a `claims.json` with a short caption + section per moment; always
   include the first frame (`00:00`).
3. Run `screenshot_pdf.py`. It downloads once, extracts every frame locally,
   and renders the PDF.
4. `Read` a couple of the JPEGs in the work dir to verify they're real content,
   then deliver the PDF.

## Requirements
- `yt-dlp`, and `ffmpeg` (or `pip install imageio-ffmpeg` for a static binary).
- `deno` + the po_token provider + `cookies.txt` — see the unblocking playbook.
- `reportlab`: `pip install reportlab`.

## Notes
- Downloads a compact **H.264** copy so the static ffmpeg decodes it without the
  AV1 segfault; frames are extracted from the **local** file (ffmpeg never hits
  the network, avoiding the static-build TLS crash).
- Same engine backs the MCP `generate_timestamped_pdf` tool and the
  `build_zip.py` package — one code path, three surfaces.

## Exit codes
`0` ok · `3` no video formats offered (IP blocked — add cookies/proxy) · `4` yt-dlp/ffmpeg missing · `5` other.
