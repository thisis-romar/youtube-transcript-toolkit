# Failure modes

| Status | Meaning | Typical fix |
|---|---|---|
| `success` | Captions were fetched and processed. | Read the artifact outputs. |
| `no_captions` | yt-dlp did not find captions for the requested language. | Try another `lang`, manual transcript input, or a future audio transcription fallback. |
| `rate_limited` | YouTube returned HTTP 429 after retries. | Add `TRANSCRIPT_PROXY_URL` or `YOUTUBE_COOKIES_TXT`. |
| `network_error` | Fetch failed before caption availability could be checked. | Check DNS, egress, proxy, certificates, and `VIDEO_ID.fetch.log`. |
| `auth_required` | Video likely needs login, age, or region credentials. | Add a valid `YOUTUBE_COOKIES_TXT` secret. |
| `tool_missing` | `yt-dlp` is unavailable. | Install `yt-dlp` in the worker. |
| `processing_error` | Fetch succeeded, but transcript processing failed. | Inspect `VIDEO_ID.fetch.log` and test processor with the raw artifact. |

The workflow always uploads artifacts on failure so the caller can inspect logs
without re-running blindly.
