#!/bin/bash
# SessionStart hook — install the youtube-toolkit access stack so transcript
# fetch and screenshot capture work in Claude Code on the web.
#
# Installs (idempotent, non-interactive, web-only):
#   - Python deps: yt-dlp, reportlab, imageio-ffmpeg, bgutil-ytdlp-pot-provider
#   - deno (JS runtime) for the yt-dlp EJS n-challenge solver
#   - best-effort: builds the bgutil po_token provider and exports
#     YT_POT_PROVIDER_HOME so the tools can auto-start it
#
# NOTE: cookies are a user secret and cannot be installed here. For screenshot
# capture (403/429 walls) you still supply YT_COOKIES or a residential YT_PROXY.
# See plugins/youtube-toolkit/resources/unblocking-youtube.md.
set -uo pipefail

# Only run in Claude Code on the web (remote); no-op locally.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Async: start the session immediately; install in the background.
echo '{"async": true, "asyncTimeout": 300000}'

log() { echo "[session-start] $*" >&2; }

# --- Python deps -----------------------------------------------------------
PIP="python3 -m pip install --quiet --disable-pip-version-check"
DEPS="yt-dlp reportlab imageio-ffmpeg bgutil-ytdlp-pot-provider ruff pytest"
log "installing Python deps ($DEPS)..."
$PIP $DEPS \
  || $PIP --break-system-packages $DEPS \
  || log "WARN: pip install had errors (continuing)"

# --- deno (JS runtime for the EJS solver) ----------------------------------
DENO_INSTALL="${DENO_INSTALL:-$HOME/.deno}"
if ! command -v deno >/dev/null 2>&1 && [ ! -x "$DENO_INSTALL/bin/deno" ]; then
  log "installing deno JS runtime..."
  curl -fsSL https://deno.land/install.sh | DENO_INSTALL="$DENO_INSTALL" sh >/dev/null 2>&1 \
    || log "WARN: deno install failed (n-challenge solving may be limited)"
fi
[ -d "$DENO_INSTALL/bin" ] && export PATH="$DENO_INSTALL/bin:$PATH"

# --- bgutil po_token provider (best-effort; needs node) --------------------
POT_HOME="$HOME/.bgutil-pot/server"
if command -v node >/dev/null 2>&1; then
  if [ ! -f "$POT_HOME/build/main.js" ]; then
    log "building bgutil po_token provider (best-effort)..."
    if git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
         "$HOME/.bgutil-pot" >/dev/null 2>&1; then
      ( cd "$POT_HOME" \
        && python3 -c "import json,sys; p=json.load(open('package.json')); p.get('dependencies',{}).pop('canvas',None); json.dump(p,open('package.json','w'))" \
        && npm install --no-optional --no-audit --no-fund >/dev/null 2>&1 \
        && npx --yes tsc >/dev/null 2>&1 ) || log "WARN: provider build failed (screenshots need a po_token)"
    fi
  fi
fi

# --- persist env for the session -------------------------------------------
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  [ -d "$DENO_INSTALL/bin" ] && echo "export PATH=\"$DENO_INSTALL/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
  [ -f "$POT_HOME/build/main.js" ] && echo "export YT_POT_PROVIDER_HOME=\"$POT_HOME\"" >> "$CLAUDE_ENV_FILE"
  [ -d /opt/pw-browsers ] && echo "export PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers" >> "$CLAUDE_ENV_FILE"
fi

log "done. yt-dlp=$(command -v yt-dlp || echo none) deno=$([ -x "$DENO_INSTALL/bin/deno" ] && echo yes || command -v deno || echo none) provider=$([ -f "$POT_HOME/build/main.js" ] && echo built || echo skipped)"
exit 0
