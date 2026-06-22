# Transcript worker operations

## Manual GitHub run

1. Open **Actions → Fetch transcript → Run workflow**.
2. Enter a YouTube URL or video ID.
3. Optionally set `lang`, `timestamps`, `no_check_certs`, and `stage`.
4. Use `stage=fetch` for a smoke test or `stage=all` to fetch and process every documented output.
5. Download the `transcript-<run_id>` artifact after the run finishes.
6. Inspect `VIDEO_ID.metadata.json` first, then read transcript outputs.

For example, use these workflow inputs to fetch and process the sample video:

| Input | Value |
|---|---|
| `youtube_url` | `https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi` |
| `lang` | `en` |
| `timestamps` | `true` |
| `stage` | `all` |

## Restricted chat or container runtimes

Some chat runtimes and local containers are intentionally not the transcript
fetch worker. They may have no GitHub workflow-dispatch connector, no DNS or
network egress to YouTube/GitHub, and no preinstalled `yt-dlp`. In that case,
do not treat the chat/container failure as a transcript failure. Dispatch the
GitHub Actions worker from the GitHub UI, or run the local command below from a
network-capable host, then upload or paste one of the output artifacts back into
the chat for downstream processing.

The worker command for the sample video is:

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi' --lang en --timestamps --stage all
```

When `stage=all` succeeds, the artifact contains this contract:

```text
DcvgPEApHT8.raw.json3
DcvgPEApHT8.timestamped.txt
DcvgPEApHT8.clean.txt
DcvgPEApHT8.segments.md
DcvgPEApHT8.metadata.json
DcvgPEApHT8.fetch.log
DcvgPEApHT8.exit_code.txt
```

## Local worker run

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8' --lang en --timestamps
```

Optional network lanes:

```bash
TRANSCRIPT_PROXY_URL='http://user:pass@host:port' \
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8' --cookies cookies.txt
```

## Status model

For GitHub-native operation, the workflow run and uploaded artifact form the
status record:

- `requested` - a user or assistant dispatches the workflow.
- `queued` - GitHub Actions has accepted the run.
- `fetching` - `tools/run_pipeline.py` is executing `yt-dlp`.
- `processing` - transcript processor outputs are being generated.
- `complete` - `metadata.json` status is `success`.
- `failed` - `metadata.json` status is any non-success value.

A future issue-based queue can mirror these states with labels and comments.

## Sample command reference

Use the pipeline command below for the sample URL when running from a
network-capable host. The `stage` flag is optional for local runs because the
pipeline defaults to the full `all` stage.

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi' --lang en --timestamps
```

The README shows the same video without YouTube's optional tracking parameter:

```bash
python3 tools/run_pipeline.py 'https://youtu.be/DcvgPEApHT8' --lang en --timestamps
```

The lower-level plugin command that the pipeline wraps is:

```bash
python3 plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py \
  'https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi' \
  --timestamps \
  --lang en \
  --out outputs/DcvgPEApHT8.timestamped.txt \
  --raw-out outputs/DcvgPEApHT8.raw.json3
```

For the sample video, the full pipeline artifact contains these paths:

```text
outputs/DcvgPEApHT8.raw.json3
outputs/DcvgPEApHT8.timestamped.txt
outputs/DcvgPEApHT8.clean.txt
outputs/DcvgPEApHT8.segments.md
outputs/DcvgPEApHT8.metadata.json
outputs/DcvgPEApHT8.fetch.log
outputs/DcvgPEApHT8.exit_code.txt
```
