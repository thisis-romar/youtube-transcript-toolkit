# Triage / RCA: transcript fetch failures by environment

Root-cause analysis for "the plugin didn't return a transcript." The short version:
**this is an environment / network-policy problem, not a plugin defect.** In every
environment tested, the request was blocked at the network/transport/policy layer *before*
captions could be retrieved, and `fetch_transcript.py` detected and classified each failure
with the correct exit code.

## Failure matrix (observed)

Same command, same video (`DcvgPEApHT8`), four environments:

| Environment | Layer that failed | Exit | Classified correctly |
|---|---|---|---|
| ChatGPT chat sandbox | DNS / egress (can't resolve `www.youtube.com`; also can't reach github.com) | `5` network_error | ✅ |
| Second agent `/mnt/data` sandbox | DNS resolution | `5` network_error | ✅ |
| GitHub Actions worker | Bot-gate ("Sign in to confirm you're not a bot") from datacenter IP → no caption tracks | `2` no_captions | ✅ |
| Networked host behind TLS proxy | TLS interception (`CERTIFICATE_VERIFY_FAILED`) → with `--no-check-certs`, HTTP **429** | `5` → `3` | ✅ |

The bot-gate surfaces as exit `2` (no captions) rather than a dedicated auth code: it is
neither a 429 nor a network error, so yt-dlp returns zero caption tracks and the script
falls through to the no-captions path. Correct given the exit-code vocabulary.

## Why it's not the code

In `plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py`:

- `is_network_error()` matches both DNS strings (`temporary failure in name resolution`,
  `name or service not known`) and TLS strings (`certificate verify failed`, `ssl:`) →
  `run_ytdlp()` exits `5`.
- The `429` branch retries with exponential backoff (4 attempts) then exits `3`.
- No `.json3` + not-429 + not-network → `run_ytdlp()` returns `None` → `main()` exits `2`.
- `resolve_credentials()` applies `flag > env > file > default`, logs the *source* (never
  the secret), and auto-detects `cookies.txt` in `$CLAUDE_PLUGIN_ROOT` or beside the script.

Each exit path fired for the correct underlying cause.

## Triage decision path (for agents/operators)

When a fetch fails, **read the exit code first** and act on it — do not reconstruct the
script or substitute a web search for the transcript:

1. **Exit 5 (network/DNS/cert).** If the message says DNS/resolve: this host has no egress
   and *cannot* fetch — stop retrying locally and **delegate** (see below). If it's a cert
   error: re-run with `--no-check-certs` (or `YT_TRANSCRIPT_NO_CHECK_CERTS=1`).
2. **Exit 3 (429) or Exit 2 (bot-gate).** The IP is gated. Supply `--cookies` /
   `YT_TRANSCRIPT_COOKIES` (logged-in session) and/or a residential `--proxy` /
   `YT_TRANSCRIPT_PROXY`, or run from a non-datacenter IP.
3. **Exit 4.** `pip install yt-dlp`.

**Delegate path** for DNS-blocked sandboxes: dispatch the GitHub Actions worker
(Actions → "Fetch transcript" → Run workflow) or run the command from a networked host.
See `docs/operations.md`.

## Remediation matrix

| Blocking layer | Exit | Fix (existing repo features) | Reliability |
|---|---|---|---|
| DNS-blocked sandbox | 5 | No local fix. Delegate to Actions worker / networked host. | Only option |
| TLS interception | 5 | `--no-check-certs` / `YT_TRANSCRIPT_NO_CHECK_CERTS=1` | High (deterministic) |
| Bot-gate ("not a bot") | 2 | `--cookies` / `YT_TRANSCRIPT_COOKIES` + residential `--proxy` | High with cookies + residential IP; datacenter IP alone will not pass |
| 429 rate-limit | 3 | Built-in backoff first; then residential `--proxy`/`--cookies` or non-DC IP | High off a residential/non-DC IP; unreliable on a datacenter IP |

**Key callouts**

- The bot-gate and the 429 are **datacenter-IP reputation gates** — only a residential
  proxy/cookies or a non-datacenter IP reliably clears them. No other flag helps.
- DNS-blocked sandboxes **cannot** fetch; the work must be delegated.
- `--no-check-certs` only fixes the TLS layer; advancing exit 5 (cert) → exit 3 (429) is
  expected progress, not a regression.
