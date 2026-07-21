# youtube-toolkit

One Claude Code plugin, three skills, one shared access layer.

| Skill | What it does |
|---|---|
| **youtube-transcript** | Fetch captions from any YouTube URL/ID (json3 → text, optional timestamps) |
| **transcript-processor** | Clean, de-dupe, and segment raw transcript text (stdlib-only, offline) |
| **video-screenshots** | Capture frames at timestamps → styled recap **PDF** |

## Why a shared access layer
YouTube (2026) gates content behind three independent walls — n-challenge,
po_token (403/DRM), and datacenter-IP 429. Rather than each skill re-solving
them, all YouTube access flows through **`scripts/ytdlp_access.py`**, which
auto-wires:

- a JS runtime (**deno**) + the yt-dlp **EJS** solver (`--remote-components ejs:npm`),
- an optional **bgutil po_token provider** (auto-detected on `:4416`, or auto-started via `YT_POT_PROVIDER_HOME`),
- **cookies / proxy** with precedence *flag > env > auto-detected file*.

Full setup is in [`resources/unblocking-youtube.md`](resources/unblocking-youtube.md).

## Layout
```
youtube-toolkit/
├── .claude-plugin/plugin.json
├── resources/
│   └── unblocking-youtube.md        ← access playbook (cookies/EJS/po_token)
├── scripts/                         ← shared by every skill + the MCP + build_zip
│   ├── ytdlp_access.py              ← the access layer
│   ├── fetch_transcript.py
│   ├── process_transcript.py
│   ├── video_frames.py              ← download + local frame extraction
│   ├── build_pdf.py                 ← reportlab recap layout (single source)
│   └── screenshot_pdf.py            ← URL + claims → frames → PDF
└── skills/
    ├── youtube-transcript/SKILL.md
    ├── transcript-processor/SKILL.md
    └── video-screenshots/SKILL.md
```

## The screenshot capability, three ways
The exact same engine (`screenshot_pdf.py` → `video_frames.py` + `build_pdf.py`)
is exposed as:
1. the **video-screenshots** skill (here),
2. the MCP `generate_timestamped_pdf` tool (`mcp-server/`),
3. a distributable zip via `build_zip.py`.
