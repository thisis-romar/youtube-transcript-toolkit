# Transcript worker operations

## Manual GitHub run

1. Open **Actions → Fetch transcript → Run workflow**.
2. Enter a YouTube URL or video ID.
3. Optionally set `lang`, `timestamps`, and `no_check_certs`.
4. Download the `transcript-<run_id>` artifact after the run finishes.
5. Inspect `VIDEO_ID.metadata.json` first, then read transcript outputs.

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
