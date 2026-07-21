#!/usr/bin/env python3
"""Shared YouTube access layer for the youtube-toolkit skills.

YouTube in 2026 gates content behind three independent walls; this module wires
past all three automatically so every skill (transcript fetch, frame capture)
gets the same battle-tested access path instead of each re-discovering it:

  1. n-challenge / signature   -> needs a JS runtime (deno) AND the yt-dlp EJS
                                  "remote component" solver. deno alone is no
                                  longer enough on recent yt-dlp.
  2. po_token (403 / DRM)       -> needs a Proof-of-Origin token. A local bgutil
                                  provider mints one with no credentials; the
                                  yt-dlp plugin auto-detects it on :4416.
  3. IP rate-limit (429)        -> a datacenter IP gets throttled to "images
                                  only". cookies.txt from a signed-in browser
                                  (or a residential --proxy) clears it.

Everything is opt-in via env / flags and degrades gracefully: with nothing
configured you still get whatever the bare client returns.

Credential precedence (per item): explicit flag > env var > auto-detected file.

Env vars (all optional):
    YT_COOKIES / YT_TRANSCRIPT_COOKIES   path to a Netscape cookies.txt
    YT_PROXY   / YT_TRANSCRIPT_PROXY      residential proxy URL (ambient HTTPS_PROXY
                                          is intentionally NOT used — see resolve_credentials)
    YT_NO_CHECK_CERTS / YT_TRANSCRIPT_NO_CHECK_CERTS   truthy -> skip cert checks
    YT_NO_EJS                            truthy -> do not add the EJS solver
    YT_EJS_SOURCE                        "npm" (default) or "github"
    YT_POT_PROVIDER_URL                  provider base URL (default http://127.0.0.1:4416)
    YT_POT_PROVIDER_HOME                 path to a built bgutil server dir; if set,
                                         pot_provider() will start it on demand
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request

DEFAULT_POT_URL = "http://127.0.0.1:4416"


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _first_env(*names: str) -> str | None:
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return None


def autodetect_cookies() -> str | None:
    """Find a cookies.txt in intentional locations (never the CWD)."""
    candidates = []
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root:
        candidates += [os.path.join(root, "cookies.txt"),
                       os.path.join(root, "scripts", "cookies.txt")]
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def resolve_credentials(proxy=None, cookies=None, no_check_certs=False, *, quiet=False):
    """Resolve (proxy, cookies, no_check_certs). Logs the *source*, never the value.

    NOTE: the ambient ``HTTPS_PROXY`` is deliberately NOT used as a YouTube proxy.
    In sandboxes it points at an egress/agent proxy that YouTube still sees as a
    datacenter IP (and can break media fetches). Set ``YT_PROXY`` explicitly to
    route through a *residential* proxy.
    """
    proxy_flag = proxy
    proxy = proxy or _first_env("YT_PROXY", "YT_TRANSCRIPT_PROXY")
    cookies_flag = cookies
    cookies = cookies or _first_env("YT_COOKIES", "YT_TRANSCRIPT_COOKIES")
    src = "flag" if cookies_flag else ("env" if cookies else None)
    if not cookies:
        cookies = autodetect_cookies()
        src = "auto-detected file" if cookies else None
    ncc = no_check_certs or env_truthy("YT_NO_CHECK_CERTS") or env_truthy("YT_TRANSCRIPT_NO_CHECK_CERTS")
    if not quiet:
        if proxy:
            print(f"[access] proxy configured (from {'flag' if proxy_flag else 'env'})", file=sys.stderr)
        if cookies and src != "flag":
            print(f"[access] using cookies from {src}: {cookies}", file=sys.stderr)
        if ncc:
            print("[access] certificate checks disabled", file=sys.stderr)
    return proxy, cookies, ncc


def has_deno() -> bool:
    return shutil.which("deno") is not None


def ejs_flags() -> list[str]:
    """`--remote-components` flags for the JS-challenge solver, when usable.

    The solver needs a JS runtime; if `deno` is absent yt-dlp can still try, so we
    only add the flag when it can actually help. Source defaults to npm because the
    GitHub raw host is often blocked by egress proxies.
    """
    if env_truthy("YT_NO_EJS") or not has_deno():
        return []
    source = (os.environ.get("YT_EJS_SOURCE") or "npm").strip().lower()
    if source not in ("npm", "github"):
        source = "npm"
    return ["--remote-components", f"ejs:{source}"]


def common_cli_flags(proxy=None, cookies=None, no_check_certs=False,
                     player_client="web", ejs=True) -> list[str]:
    """Build the shared yt-dlp CLI flags used by every subprocess caller."""
    flags = ["--extractor-args", f"youtube:player_client={player_client}"]
    if ejs:
        flags += ejs_flags()
    if proxy:
        flags += ["--proxy", proxy]
    if cookies:
        flags += ["--cookies", cookies]
    if no_check_certs:
        flags += ["--no-check-certificates"]
    return flags


def pot_provider_url() -> str:
    return (os.environ.get("YT_POT_PROVIDER_URL") or DEFAULT_POT_URL).rstrip("/")


def pot_provider_reachable(url: str | None = None, timeout: float = 2.0) -> bool:
    url = (url or pot_provider_url()) + "/ping"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


@contextlib.contextmanager
def pot_provider():
    """Ensure a bgutil po_token provider is reachable for the duration.

    - If one is already reachable, use it and leave it running.
    - Else if YT_POT_PROVIDER_HOME points at a built bgutil server, start it and
      stop it on exit.
    - Else yield with no provider (yt-dlp still runs; frames may 403 on a blocked IP).
    """
    url = pot_provider_url()
    if pot_provider_reachable(url):
        print(f"[access] po_token provider already up at {url}", file=sys.stderr)
        yield url
        return

    home = os.environ.get("YT_POT_PROVIDER_HOME")
    main_js = os.path.join(home, "build", "main.js") if home else None
    node = shutil.which("node")
    if not (main_js and os.path.isfile(main_js) and node):
        if home:
            print("[access] YT_POT_PROVIDER_HOME set but build/main.js or node missing; "
                  "continuing without a provider", file=sys.stderr)
        yield None
        return

    port = url.rsplit(":", 1)[-1] if ":" in url else "4416"
    proc = subprocess.Popen([node, main_js, "--port", port],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(10):
            if pot_provider_reachable(url):
                print(f"[access] started po_token provider at {url}", file=sys.stderr)
                break
            time.sleep(1)
        yield url if pot_provider_reachable(url) else None
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)


def require_ytdlp() -> None:
    if not shutil.which("yt-dlp") and not _module_ytdlp():
        print("yt-dlp not installed: pip install yt-dlp", file=sys.stderr)
        sys.exit(4)


def _module_ytdlp() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except Exception:
        return False


def ytdlp_cli() -> list[str]:
    """Prefer the console script; fall back to `python -m yt_dlp`."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]
