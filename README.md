# youtube-transcript-toolkit

Fetch, clean, and visualize YouTube content across Claude Code and Claude.ai —
transcripts, cleanup, and **timestamped screenshot PDFs** — behind one auto-wiring
access layer that survives YouTube's 2026 gating.

## One plugin, three skills

Everything now lives in a single Claude Code plugin, **`plugins/youtube-toolkit`**:

| Skill | What it does |
|---|---|
| `youtube-transcript` | Fetch captions from any YouTube URL/ID (json3 → text, optional timestamps) |
| `transcript-processor` | Clean, de-dupe, segment raw transcript text (stdlib-only, offline) |
| `video-screenshots` | Capture frames at timestamps → styled recap **PDF** |

All three share one code path under `plugins/youtube-toolkit/scripts/`, including
**`ytdlp_access.py`**, the access layer described below.

---

## The access layer (why this works when naive tools 403/429)

YouTube gates content behind three independent walls. `ytdlp_access.py` wires past
all of them automatically; skills never re-solve them:

| Wall | Symptom | Cleared by |
|---|---|---|
| n-challenge / signature | `n challenge solving failed` | **deno** + yt-dlp **EJS** solver (`--remote-components ejs:npm`) |
| po_token (403 / DRM) | `HTTP 403` on media bytes | local **bgutil** provider (auto-detected on `:4416`, or auto-started via `YT_POT_PROVIDER_HOME`) |
| IP rate-limit (429) | `HTTP 429`, "Only images are available" | **cookies.txt** (`YT_COOKIES`) or a residential **`YT_PROXY`** |

Transcripts usually clear with just the first wall; **screenshots need all three**
(they download real video bytes). Full setup:
[`plugins/youtube-toolkit/resources/unblocking-youtube.md`](plugins/youtube-toolkit/resources/unblocking-youtube.md).

---

## Claude Code — install

**Via marketplace (shareable):**
```
/plugin marketplace add thisis-romar/youtube-transcript-toolkit
/plugin install youtube-toolkit@romar-tools
```

**Local, instant:**
```bash
cp -r plugins/youtube-toolkit ~/.claude/plugins/
```

### Prerequisites
```bash
pip install yt-dlp reportlab imageio-ffmpeg
curl -fsSL https://deno.land/install.sh | sh     # JS runtime for the EJS solver
```

### Usage
```bash
# Transcript
python3 plugins/youtube-toolkit/scripts/fetch_transcript.py \
    "https://youtu.be/DcvgPEApHT8" --timestamps

# Screenshots → recap PDF (needs cookies for the 429 wall — see the playbook)
export YT_COOKIES=/secure/path/cookies.txt
python3 plugins/youtube-toolkit/scripts/screenshot_pdf.py \
    "https://youtu.be/DcvgPEApHT8" --timestamps 0,6:00,32:30 -o recap.pdf

# Clean a raw transcript (offline, stdlib-only)
python3 plugins/youtube-toolkit/scripts/process_transcript.py raw.txt --mode clean
```

---

## The screenshot capability, three surfaces (one engine)

`screenshot_pdf.py` → `video_frames.py` (download + local frame extraction) →
`build_pdf.py` (reportlab layout) is exposed as:

1. the **video-screenshots** skill (above),
2. the MCP `generate_timestamped_pdf` tool — `mcp-server/`,
3. a distributable zip — `python3 build_zip.py` → `youtube_mcp_plugin.zip`.

### MCP server
Holds credentials in its launch env so they never appear at the call site.
```bash
pip install -r mcp-server/requirements.txt
claude mcp add youtube-toolkit \
  --env YT_COOKIES=/secure/path/cookies.txt \
  -- python3 /abs/path/to/mcp-server/youtube_transcript_server.py
```
Exposes `fetch_transcript` and `generate_timestamped_pdf`.

---

## Claude.ai — processor skill

The `transcript-processor` skill is stdlib-only (no network, no pip), so it runs
in the Claude.ai code-execution sandbox on any egress setting. Upload
`plugins/youtube-toolkit/skills/transcript-processor` (with the shared
`scripts/process_transcript.py`) or run it locally:
```bash
python3 plugins/youtube-toolkit/scripts/process_transcript.py raw.txt --mode clean
```
Modes: `clean` (default), `timestamped`, `sentences`, `paragraphs`.
Supported input (auto-detected): VTT · SRT · json3 · `[HH:MM:SS]` bracketed · plain text.

---

## Worker-first architecture (optional)

For restricted chat sandboxes, a GitHub Actions worker and local pipeline runner
fetch and publish artifacts under `outputs/`. See `docs/architecture.md`,
`docs/rollout.md`, `docs/operations.md`, and `docs/failure-modes.md`.

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8' --lang en --timestamps
```

---

## Repo layout
```
youtube-transcript-toolkit/
├── .claude-plugin/marketplace.json         ← romar-tools marketplace
├── plugins/
│   └── youtube-toolkit/                     ← the plugin (3 skills, shared engine)
│       ├── .claude-plugin/plugin.json
│       ├── resources/unblocking-youtube.md  ← access playbook
│       ├── scripts/                         ← shared by skills + MCP + build_zip
│       │   ├── ytdlp_access.py
│       │   ├── fetch_transcript.py
│       │   ├── process_transcript.py
│       │   ├── video_frames.py
│       │   ├── build_pdf.py
│       │   └── screenshot_pdf.py
│       └── skills/
│           ├── youtube-transcript/SKILL.md
│           ├── transcript-processor/SKILL.md
│           └── video-screenshots/SKILL.md
├── mcp-server/                              ← MCP wrapper (both tools)
├── build_zip.py                             ← packages the screenshot engine
├── tools/  ·  docs/  ·  outputs/  ·  .github/workflows/
```
