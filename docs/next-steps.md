# Retrieving the YouTube Transcript — Next Steps

**Repository:** `thisis-romar/youtube-transcript-toolkit`  ·  **Video:** `DcvgPEApHT8`
**Date:** 2026-06-22

## Why these are the next steps

Testing the fetch plugin across four environments showed the transcript fetch is blocked
only by **network policy and IP reputation** — never by a code defect. The plugin detected
and classified every failure correctly:

| Environment | Blocked at | Exit code |
|---|---|---|
| ChatGPT / agent sandbox | DNS / no egress | `5` network_error |
| GitHub Actions worker | Datacenter-IP bot-gate ("Sign in to confirm you're not a bot") | `2` no_captions |
| Networked host behind TLS proxy | TLS interception → (with `--no-check-certs`) HTTP 429 | `5` → `3` |

So the remaining work is purely to **present a trusted identity / clean IP** (cookies and/or
a residential proxy) or to **delegate to a host that has egress** (the Actions worker), then
run and process the result.

## Decision tree

1. **Exit 5 with a DNS / "failed to resolve" message** → this host has no egress; it cannot
   fetch. Delegate to the GitHub Actions worker or a networked machine (Step 3).
2. **Exit 5 with a certificate error** → you are behind a TLS-intercepting proxy. Re-run with
   `--no-check-certs` (or `YT_TRANSCRIPT_NO_CHECK_CERTS=1`).
3. **Exit 2 (bot-gate) or Exit 3 (429)** → the IP is gated. Supply cookies (Step 1) and/or a
   residential proxy (Step 2).
4. **Exit 4** → `pip install yt-dlp`.

---

## Step 1 — Cookies (defeats the bot-gate; usually clears 429)

A `cookies.txt` from a signed-in session makes yt-dlp authenticate as a real account, which
clears YouTube's "Sign in to confirm you're not a bot" gate.

> ⚠️ Use a **throwaway / secondary** Google account. Per the yt-dlp wiki, "By using your
> account with yt-dlp, you run the risk of it being banned (temporarily or permanently)."
> Export from a **private browsing window** to stop YouTube rotating the cookies. [2]

### Export the cookies

**Browser extension (recommended).** Install a "Get cookies.txt" extension that exports in
**Netscape/Mozilla format**, sign in to youtube.com, then export `cookies.txt`. The file must
be Netscape-formatted with the correct line endings (LF on Unix). [1][2]

**Or via yt-dlp directly** (reads your browser profile):

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download \
  "https://youtu.be/DcvgPEApHT8"
```

Per the yt-dlp README, `--cookies FILE` is a "Netscape formatted file to read cookies from",
and `--cookies-from-browser BROWSER` loads cookies from a supported browser
(brave, chrome, chromium, edge, firefox, opera, safari, vivaldi, whale). [3]

### Apply the cookies

**A. Local / this environment (set once):**

```bash
export YT_TRANSCRIPT_COOKIES=/secure/path/cookies.txt
python3 plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py \
  "https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi" --timestamps --no-check-certs \
  --out DcvgPEApHT8_transcript.txt --raw-out DcvgPEApHT8_raw.json3
```

The script also auto-detects a `cookies.txt` placed in `${CLAUDE_PLUGIN_ROOT}` or beside the
script — no flag needed.

**B. GitHub Actions worker (repo secret):** add a repository secret named
**`YOUTUBE_COOKIES_TXT`** containing the full file contents. In the repo: **Settings →
Secrets and variables → Actions → New repository secret**. [4][5]

```bash
gh secret set YOUTUBE_COOKIES_TXT \
  --repo thisis-romar/youtube-transcript-toolkit < cookies.txt
```

---

## Step 2 — Residential proxy (the surest defeat for 429 / bot-gate)

Both the bot-gate and the 429 are datacenter-IP reputation gates; routing through a
**residential** proxy presents a clean IP.

`--proxy URL` uses the specified HTTP/HTTPS/SOCKS proxy, e.g.
`socks5://user:pass@127.0.0.1:1080/`. [3]

**Local / this environment (set once):**

```bash
export YT_TRANSCRIPT_PROXY="http://user:pass@host:port"
python3 plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py \
  "https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi" --timestamps --no-check-certs
```

**GitHub Actions worker:** add the secret **`TRANSCRIPT_PROXY_URL`** (the workflow reads it
into the run). [4][5]

---

## Step 3 — Delegate to the GitHub Actions worker (for DNS-blocked hosts)

When the current host has no egress at all (exit 5 / DNS), run the worker, which executes on
a network-capable runner and uploads the transcript as an artifact.

**Web UI:** repo → **Actions** → **Fetch transcript** → **Run workflow** → pick branch `main`,
fill inputs, **Run workflow**. Manual runs require the workflow to use `workflow_dispatch` and
the caller to have **write** access. [6]

**GitHub CLI:** use `gh workflow run` with `-f key=value` inputs. [6]

```bash
gh workflow run fetch-transcript.yml \
  --repo thisis-romar/youtube-transcript-toolkit --ref main \
  -f youtube_url="https://youtu.be/DcvgPEApHT8?si=jHJ6EZPwrBHNFpPi" \
  -f lang=en -f timestamps=true -f no_check_certs=false -f stage=fetch

# then download the artifact once the run completes:
gh run list  --repo thisis-romar/youtube-transcript-toolkit --workflow fetch-transcript.yml -L 1
gh run download <run-id> --repo thisis-romar/youtube-transcript-toolkit
```

> Note: GitHub-hosted runners use datacenter IPs, so the worker may still hit the bot-gate or
> 429 unless `YOUTUBE_COOKIES_TXT` or `TRANSCRIPT_PROXY_URL` (Steps 1–2) is set.

---

## Step 4 — Zero-touch via the MCP server

For repeated use without passing flags or secrets at the call site, register the bundled MCP
server and set the credentials on its launch environment. Claude then calls a
`fetch_transcript` tool with just a URL.

`claude mcp add` registers a server; `--env` sets environment variables on it. [7]

```bash
claude mcp add youtube-transcript \
  --env YT_TRANSCRIPT_COOKIES=/secure/path/cookies.txt \
  --env YT_TRANSCRIPT_NO_CHECK_CERTS=1 \
  -- python3 /abs/path/to/mcp-server/youtube_transcript_server.py
```

See `mcp-server/README.md` in the repo for the `.mcp.json` equivalent.

---

## Step 5 — Verify and process

A successful fetch exits `0` and writes a populated `*.timestamped.txt` plus the raw
`*.json3`. Then clean it with the offline processor skill:

```bash
python3 skills/transcript-processor/scripts/process_transcript.py \
  DcvgPEApHT8_transcript.txt --mode timestamped
```

Modes: `clean` (default), `timestamped`, `sentences`, `paragraphs`.

---

## Security notes

- Treat `cookies.txt` as account credentials and the proxy URL as a secret. Use a **burner**
  Google account.
- Secrets are read from the environment / external files only — never committed. `cookies.txt`,
  `*.cookies.txt`, and `.env` are git-ignored in this repo.
- Repository secrets are encrypted with Libsodium sealed boxes before reaching GitHub. [4][5]
- After fetching, revoke the burner account's sessions (Google Account → Security → "Sign out
  of all devices") and/or delete the secret.

---

## Sources

1. yt-dlp — FAQ, "How do I pass cookies to yt-dlp?": https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
2. yt-dlp — Extractors, "Exporting YouTube cookies": https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies
3. yt-dlp — README (option reference for `--proxy`, `--cookies`, `--cookies-from-browser`): https://github.com/yt-dlp/yt-dlp
4. GitHub Docs — Using secrets in GitHub Actions: https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions
5. GitHub Docs — Secrets (concept): https://docs.github.com/en/actions/concepts/security/secrets
6. GitHub Docs — Manually running a workflow: https://docs.github.com/en/actions/how-tos/managing-workflow-runs-and-deployments/managing-workflow-runs/manually-running-a-workflow
7. Claude Code — Connect Claude Code to tools via MCP: https://code.claude.com/docs/en/mcp
