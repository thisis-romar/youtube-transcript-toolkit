# youtube-transcript-toolkit

Fetch, clean, and process YouTube transcripts across Claude Code and Claude.ai.

Two tools, one repo — pick the one that matches your surface:

| Tool | Surface | What it does |
|---|---|---|
| `plugins/youtube-transcript` | **Claude Code** | Fetches captions from any YouTube URL via yt-dlp |
| `skills/transcript-processor` | **Claude.ai** | Cleans, de-dupes, and segments raw transcript text |

---

## Worker-first architecture

ChatGPT or Claude should orchestrate transcript fetching rather than run the
network fetch directly from a restricted chat sandbox. The repository now
includes a GitHub Actions worker and local pipeline runner that fetch captions,
process them, and publish stable artifacts for the assistant to inspect.

```text
ChatGPT / Claude -> GitHub workflow or worker API -> yt-dlp worker -> outputs/ artifacts
```

Run the pipeline locally from a network-capable host:

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8' --lang en --timestamps
```

Or dispatch `.github/workflows/fetch-transcript.yml` with `youtube_url`, `lang`,
`timestamps`, and rollout `stage` inputs. Start with `stage=fetch` for the
minimal client smoke test, then use `stage=all` after artifact retrieval works.
Configure `TRANSCRIPT_PROXY_URL` and
`YOUTUBE_COOKIES_TXT` repository secrets for 429, age-gated, region-gated, or
authenticated videos. Each run writes an artifact contract under `outputs/`:

```text
VIDEO_ID.raw.json3
VIDEO_ID.timestamped.txt
VIDEO_ID.clean.txt
VIDEO_ID.segments.md
VIDEO_ID.metadata.json
VIDEO_ID.fetch.log
VIDEO_ID.exit_code.txt
```

See `docs/architecture.md`, `docs/rollout.md`, `docs/operations.md`, and
`docs/failure-modes.md` for the worker pattern, staged rollout, and operational
details.

---

## Claude Code — fetch plugin

Fetches the spoken transcript of any YouTube video or Short. Built to survive
YouTube's two current breakages: stripped caption tracks on naive clients, and
`timedtext` HTTP 429 rate limits.

### Install

**Option A — via marketplace (shareable with team):**
```
/plugin marketplace add thisis-romar/youtube-transcript-toolkit
/plugin install youtube-transcript@romar-tools
```

**Option B — local, instant:**
```bash
cp -r plugins/youtube-transcript ~/.claude/skills/
```
Auto-loads on the next session as `youtube-transcript@skills-dir`.

### Prerequisites
```bash
pip install yt-dlp
# Recommended for clean extraction:
curl -fsSL https://deno.land/install.sh | sh
```

### Usage
```bash
# Claude invokes it automatically, or run directly:
python3 plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py \
    https://youtube.com/shorts/doW4vHDR9JA --timestamps
```

### Reliability notes
- `--extractor-args youtube:player_client=android_vr,tv,web` surfaces caption
  tracks; default clients return zero.
- Exit code 3 (HTTP 429) means the host IP is rate-limited.
  Use `--proxy <residential>` or `--cookies cookies.txt`.
- Behind a TLS-intercepting proxy: `--no-check-certs`.

---

## Claude.ai — processor skill

Cleans raw transcript text: removes rolling auto-caption duplication, strips
non-speech annotations (`[music]`, `(applause)`, `♪`), rebuilds sentences, and
re-attaches timestamps. Stdlib-only — no network, no pip install, always runs in
the Claude.ai sandbox regardless of egress settings.

### Install (Claude.ai)
Settings → Capabilities → enable Code execution → upload
`skills/transcript-processor` as a zip.

Or use the pre-built zip if available: `transcript-processor-skill.zip`.

### Usage (local CLI)
```bash
python3 skills/transcript-processor/scripts/process_transcript.py \
    raw.txt --mode clean

# or pipe:
cat raw.txt | python3 skills/transcript-processor/scripts/process_transcript.py \
    --mode timestamped
```
Modes: `clean` (default), `timestamped`, `sentences`, `paragraphs`.
No install step — Python 3 stdlib only.

### Supported input formats (auto-detected)
VTT · SRT · json3 · `[HH:MM:SS]` bracketed · plain text

---

## Repo layout
```
youtube-transcript-toolkit/
├── .github/workflows/fetch-transcript.yml
├── docs/
├── tools/
├── outputs/
├── .claude-plugin/
│   └── marketplace.json          ← Claude Code marketplace entry
├── plugins/
│   └── youtube-transcript/       ← Claude Code fetch plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/youtube-transcript/
│           ├── SKILL.md
│           └── scripts/
│               └── fetch_transcript.py
└── skills/
    └── transcript-processor/     ← Claude.ai processor skill
        ├── SKILL.md
        └── scripts/
            └── process_transcript.py
```

