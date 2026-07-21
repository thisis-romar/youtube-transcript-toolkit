"""Unit tests for the shared access layer (ytdlp_access.py)."""
import ytdlp_access as access


def test_env_truthy(monkeypatch):
    monkeypatch.setenv("X", "1")
    assert access.env_truthy("X")
    monkeypatch.setenv("X", "TRUE")
    assert access.env_truthy("X")
    monkeypatch.setenv("X", "off")
    assert not access.env_truthy("X")
    monkeypatch.delenv("X", raising=False)
    assert not access.env_truthy("X")


def test_ejs_flags_when_deno_present(monkeypatch):
    monkeypatch.setattr(access, "has_deno", lambda: True)
    monkeypatch.delenv("YT_NO_EJS", raising=False)
    monkeypatch.delenv("YT_EJS_SOURCE", raising=False)
    assert access.ejs_flags() == ["--remote-components", "ejs:npm"]


def test_ejs_flags_source_override(monkeypatch):
    monkeypatch.setattr(access, "has_deno", lambda: True)
    monkeypatch.setenv("YT_EJS_SOURCE", "github")
    assert access.ejs_flags() == ["--remote-components", "ejs:github"]


def test_ejs_flags_disabled_or_no_deno(monkeypatch):
    monkeypatch.setattr(access, "has_deno", lambda: True)
    monkeypatch.setenv("YT_NO_EJS", "1")
    assert access.ejs_flags() == []
    monkeypatch.delenv("YT_NO_EJS", raising=False)
    monkeypatch.setattr(access, "has_deno", lambda: False)
    assert access.ejs_flags() == []


def test_common_cli_flags_order_and_content(monkeypatch):
    monkeypatch.setattr(access, "has_deno", lambda: False)  # keep EJS out of this assertion
    flags = access.common_cli_flags(proxy="http://p", cookies="c.txt",
                                    no_check_certs=True, player_client="web")
    assert flags[:2] == ["--extractor-args", "youtube:player_client=web"]
    assert "--proxy" in flags and flags[flags.index("--proxy") + 1] == "http://p"
    assert "--cookies" in flags and flags[flags.index("--cookies") + 1] == "c.txt"
    assert "--no-check-certificates" in flags


def test_resolve_credentials_flag_beats_env(monkeypatch):
    monkeypatch.setenv("YT_COOKIES", "/env/c.txt")
    proxy, cookies, ncc = access.resolve_credentials(cookies="/flag/c.txt", quiet=True)
    assert cookies == "/flag/c.txt"


def test_resolve_credentials_uses_env_cookies(monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("YT_COOKIES", "/env/c.txt")
    _, cookies, _ = access.resolve_credentials(quiet=True)
    assert cookies == "/env/c.txt"


def test_https_proxy_not_used_as_youtube_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://agent-proxy:8080")
    monkeypatch.delenv("YT_PROXY", raising=False)
    monkeypatch.delenv("YT_TRANSCRIPT_PROXY", raising=False)
    proxy, _, _ = access.resolve_credentials(quiet=True)
    assert proxy is None


def test_pot_provider_url_default_and_override(monkeypatch):
    monkeypatch.delenv("YT_POT_PROVIDER_URL", raising=False)
    assert access.pot_provider_url() == access.DEFAULT_POT_URL
    monkeypatch.setenv("YT_POT_PROVIDER_URL", "http://host:9999/")
    assert access.pot_provider_url() == "http://host:9999"
