# Staged rollout plan

The minimal architecture change is not the full production pipeline. The first
safe milestone is proving that ChatGPT can trigger a network-capable worker and
retrieve its artifacts. Processing, queues, and fallback transcription can follow
after that client test passes.

## Stage 1: fetch worker smoke test

Goal: validate the execution environment and trigger path.

- Use `.github/workflows/fetch-transcript.yml` with `stage=fetch`.
- Provide `youtube_url`, leave `lang=en`, and keep `timestamps=true`.
- Expected artifacts:
  - `VIDEO_ID.raw.json3`
  - `VIDEO_ID.timestamped.txt`
  - `VIDEO_ID.metadata.json`
  - `VIDEO_ID.fetch.log`
  - `VIDEO_ID.exit_code.txt`
- Client acceptance test: the assistant can dispatch the workflow, wait for it
  to complete, download the artifact, read `metadata.json`, and summarize the
  timestamped transcript.

This stage intentionally skips `clean.txt` and `segments.md`; those are not
needed to prove the blocker has moved out of the chat sandbox.

## Stage 2: full caption pipeline

Goal: validate file-based handoff between fetch and processing.

- Re-run the same workflow with `stage=all`.
- Expected additional artifacts:
  - `VIDEO_ID.clean.txt`
  - `VIDEO_ID.segments.md`
- Client acceptance test: compare raw timestamped output with cleaned/segmented
  output and confirm the assistant reads the processed artifact first.

## Stage 3: reliability lanes

Goal: handle common YouTube failures without changing the assistant flow.

- Add `TRANSCRIPT_PROXY_URL` for IP-based 429s.
- Add `YOUTUBE_COOKIES_TXT` for login, age, region, or token-gated videos.
- Test known cases for `success`, `no_captions`, and `rate_limited` statuses.

## Stage 4: request tracking

Goal: make repeated requests auditable.

- Add an issue/comment queue or `runs/VIDEO_ID/status.json` records.
- Keep artifact names unchanged so earlier clients do not break.

## Stage 5: non-caption fallback

Goal: support videos without usable captions.

- Add a separate audio/transcription worker mode.
- Keep it opt-in because it is heavier and has additional storage/runtime and
  rights considerations.

## Recommendation

Ship Stage 1 first. It is the smallest end-to-end proof that the new architecture
works: ChatGPT orchestrates, a worker fetches, artifacts return, and ChatGPT reads
the result. Only after that passes should we enable `stage=all` by default.
