# Transcript worker architecture

The toolkit is designed around orchestration rather than direct fetching from a
chat sandbox. ChatGPT, Claude, or another assistant should trigger a
network-capable worker and then inspect the worker's artifacts.

```text
User / ChatGPT
   |
   | 1. Submit YouTube URL
   v
GitHub Workflow Dispatch / Worker API
   |
   | 2. Normalize video ID
   v
Transcript Worker
   |
   | 3. Run yt-dlp caption fetch
   |    - forced YouTube clients
   |    - optional cookies
   |    - optional proxy
   v
Raw caption file
   |
   | 4. Process transcript
   |    - clean
   |    - de-dupe
   |    - timestamp
   |    - segment
   v
Artifacts
   |
   | 5. ChatGPT/GitHub retrieves outputs
   v
Markdown / TXT / JSON
```

## Why a worker is required

The fetch runtime must be able to reach YouTube reliably. Many chat execution
sandboxes cannot resolve or connect to YouTube consistently, and datacenter IPs
can be rate-limited by the `timedtext` endpoint. The local plugin script remains
the caption fetcher, but the environment that runs it should be GitHub Actions,
a VPS, Cloud Run, Fly.io, Render, or a trusted local machine.

## Pipeline stages

1. `01_fetch_raw_caption` - run `yt-dlp` through
   `plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py`.
2. `02_normalize_caption` - parse YouTube json3 into timestamped text.
3. `03_clean_transcript` - remove rolling duplicates and non-speech markers with
   `skills/transcript-processor/scripts/process_transcript.py`.
4. `04_segment_transcript` - emit paragraph/segment markdown from the cleaned
   transcript.
5. `05_export_outputs` - persist logs, metadata, exit code, and transcript files.

`tools/run_pipeline.py` ties these stages together for worker environments.

## Artifact contract

Each worker run writes predictable files under `outputs/` using the video ID as
the prefix:

```text
outputs/
  VIDEO_ID.raw.json3
  VIDEO_ID.timestamped.txt
  VIDEO_ID.clean.txt
  VIDEO_ID.segments.md
  VIDEO_ID.metadata.json
  VIDEO_ID.fetch.log
  VIDEO_ID.exit_code.txt
```

The metadata file is the stable object assistants should inspect first:

```json
{
  "video_id": "DcvgPEApHT8",
  "source_url": "https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi",
  "lang": "en",
  "fetch_runtime": "github_actions",
  "tool": "yt-dlp",
  "status": "success",
  "created_at": "2026-06-22T00:00:00+00:00"
}
```

Supported statuses are `success`, `no_captions`, `rate_limited`,
`network_error`, `auth_required`, `tool_missing`, `processing_error`, and
`failed`.

## GitHub Actions worker

`.github/workflows/fetch-transcript.yml` is manually dispatchable with these
inputs:

- `youtube_url` - required YouTube URL or 11-character video ID.
- `lang` - optional caption language prefix, default `en`.
- `timestamps` - optional timestamped output toggle, default `true`.
- `no_check_certs` - optional TLS workaround for intercepted networks.
- `stage` - rollout stage, `fetch` for the minimal worker smoke test or `all`
  for fetch plus transcript processing.

The workflow uploads `outputs/` as an artifact even when the pipeline fails so
callers can read `metadata.json`, `fetch.log`, and `exit_code.txt`.

## Cookie and proxy lanes

Configure these repository secrets when needed:

- `TRANSCRIPT_PROXY_URL` - passed to `yt-dlp --proxy` to work around IP-based
  429s or regional routing problems.
- `YOUTUBE_COOKIES_TXT` - written to a private `cookies.txt` file and passed to
  `yt-dlp --cookies` for age, region, login, or PO-token gated videos.

Do not commit cookies or proxy credentials.

## Future fallback modes

The primary path is captions through `yt-dlp`. Production deployments can add a
separate heavy worker mode for videos without captions:

1. Try manually provided captions/transcript text.
2. Download permitted audio.
3. Transcribe with Whisper or faster-whisper.
4. Send the generated transcript through the same processor pipeline.

Keep this fallback separate because audio download/transcription has higher
runtime, storage, and rights considerations.
