# Unblocking YouTube (2026 access playbook)

Every skill in this plugin that talks to YouTube routes through
`scripts/ytdlp_access.py`, which wires past the three independent walls YouTube
now puts in front of content. This document is the reference for what those
walls are and how to configure the way through them. Nothing here requires
editing code — it's all env vars / files, resolved with precedence
**explicit flag > env var > auto-detected file**.

## The three walls

| Wall | Symptom | What clears it |
|---|---|---|
| **1. n-challenge / signature** | `n challenge solving failed`, formats missing | A JS runtime (**deno**) **plus** the yt-dlp **EJS remote-component** solver. On recent yt-dlp, deno alone is not enough. |
| **2. po_token (403 / DRM)** | `HTTP 403 Forbidden` on the media bytes; `This video is DRM protected` | A **Proof-of-Origin token**. A local **bgutil** provider mints one with no credentials; the yt-dlp plugin auto-detects it at `http://127.0.0.1:4416`. |
| **3. IP rate-limit (429)** | `HTTP 429`, `Only images are available` | **cookies.txt** from a signed-in browser (best) or a **residential proxy**. A datacenter IP alone gets throttled to storyboard images. |

Transcripts usually clear with just wall 1 (captions come from a less-gated
endpoint). **Frame/screenshot capture needs all three**, because it downloads
the actual video bytes.

## One-time setup

### JS runtime + EJS solver (wall 1)
```bash
curl -fsSL https://deno.land/install.sh | sh      # puts `deno` on PATH
```
The access layer then adds `--remote-components ejs:npm` automatically (npm, not
github, because the GitHub raw host is often blocked by egress proxies). Disable
with `YT_NO_EJS=1`; switch source with `YT_EJS_SOURCE=github`.

### po_token provider (wall 2)
```bash
pip install bgutil-ytdlp-pot-provider           # the yt-dlp client plugin
git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider
cd bgutil-ytdlp-pot-provider/server && npm install --no-optional && npx tsc
# note: the `canvas` dep is unused by the token path; drop it from package.json
#       if it fails to build (no system cairo/pango).
export YT_POT_PROVIDER_HOME="$PWD"              # lets pot_provider() auto-start it
```
If a provider is already running the tools reuse it; otherwise, with
`YT_POT_PROVIDER_HOME` set they start it for the duration and stop it after.

### cookies / proxy (wall 3)
Export `cookies.txt` from a browser signed in to YouTube (e.g. the
"Get cookies.txt LOCALLY" extension, ideally from a private window you then
close without logging out), then point the tools at it:
```bash
export YT_COOKIES=/secure/path/cookies.txt       # or drop cookies.txt in ${CLAUDE_PLUGIN_ROOT}
# or, instead of cookies, a residential egress:
export YT_PROXY=http://user:pass@residential-host:port
```
Cookies are long-lived (weeks–months); refresh only when a fetch starts failing
with an auth error. On your own machine you can skip manual export entirely with
yt-dlp's `--cookies-from-browser edge`.

## Environment variable reference

| Var | Purpose |
|---|---|
| `YT_COOKIES` (`YT_TRANSCRIPT_COOKIES`) | path to a Netscape `cookies.txt` |
| `YT_PROXY` (`YT_TRANSCRIPT_PROXY`) | residential proxy URL (ambient `HTTPS_PROXY` is **not** auto-used — it's a datacenter egress YouTube still 429s) |
| `YT_NO_CHECK_CERTS` (`YT_TRANSCRIPT_NO_CHECK_CERTS`) | truthy → skip cert checks (TLS-intercepting proxy) |
| `YT_NO_EJS` | truthy → don't add the EJS solver |
| `YT_EJS_SOURCE` | `npm` (default) or `github` |
| `YT_POT_PROVIDER_URL` | provider base URL (default `http://127.0.0.1:4416`) |
| `YT_POT_PROVIDER_HOME` | built bgutil server dir; enables auto-start |

## Security

Secrets are read from the environment / files only — never hard-coded or
committed. `cookies.txt` and `.env` are git-ignored. For the MCP server, set
these on the server's launch env so they never appear at the call site. A
cookies file is a live session key: keep it private, and retire it (sign out of
the private window) when done.
