"""Network configuration for the scraper.

Deliberately scoped. Google rate-limits the Ads Transparency Center per source
IP, so a blocked network needs to borrow another one — but routing the whole
machine through a proxy to fix one host is both a privacy change and a way to
break unrelated tools. So this never reads the ambient HTTP_PROXY/ALL_PROXY, and
only this package's own requests are ever proxied.

Resolution order:

1. ``GOOGLE_ADS_TRANSPARENCY_PROXY`` if set pins a single route. Use ``direct``
   (or ``none``) to force a straight connection.
2. Otherwise the scraper walks an ordered route chain, advancing when a route
   is banned or unreachable:

   - **residential** — a rotating residential proxy (any provider), read from
     ``~/.config/google-ads-transparency/residential-proxy``. Every request
     exits from a different household IP, so per-IP bans cannot stick. First
     because it is the only route that cannot be burned.
   - **direct** — the machine's own connection. Free, but one static IP.
   - **tunnel** — a SOCKS relay to a remote host (see
     scripts/socks_over_ssh.py), if something is listening on the default
     tunnel address. Last resort: its exit is one static datacenter
     IP, the most bannable address class there is (both its v4 and v6 have
     been banned before).

The probes are local connect checks / file reads with short timeouts, so a
missing tunnel or creds file costs nothing and the chain simply shortens.

The ``h`` in ``socks5h`` is load-bearing. socks5h resolves DNS at the proxy;
socks5 resolves it locally. When a local resolver nulls out ad hosts — NextDNS
does this to tpc.googlesyndication.com — only socks5h can reach them.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

PROXY_ENV_VAR = "GOOGLE_ADS_TRANSPARENCY_PROXY"

# Typically scripts/socks_over_ssh.py, kept up by a launchd agent or systemd unit.
DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 1080
DEFAULT_PROXY_URL = f"socks5h://{DEFAULT_PROXY_HOST}:{DEFAULT_PROXY_PORT}"

# One line: the full rotating-residential proxy URL, credentials included.
# Lives outside the repo so it can never be committed.
RESIDENTIAL_PROXY_FILE = Path(
    "~/.config/google-ads-transparency/residential-proxy"
).expanduser()

# Routes whose egress IP changes per request; bans on these never stick, so
# the scraper retries them in place instead of advancing past them.
ROTATING_ROUTES = {"residential"}

_DISABLED = {"direct", "none", "off", "no"}


def _tunnel_is_up(timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection(
            (DEFAULT_PROXY_HOST, DEFAULT_PROXY_PORT), timeout
        ):
            return True
    except OSError:
        return False


def _residential_url() -> str:
    try:
        return RESIDENTIAL_PROXY_FILE.read_text().strip()
    except OSError:
        return ""


def proxy_routes() -> list[tuple[str, str]]:
    """Ordered ``(name, url)`` egress routes; ``""`` as url means direct.

    An explicit env var pins the chain to that single route so tests and
    one-off overrides behave exactly as before.
    """
    configured = os.environ.get(PROXY_ENV_VAR, "").strip()
    if configured:
        if configured.lower() in _DISABLED:
            return [("direct", "")]
        return [("env", configured)]
    routes: list[tuple[str, str]] = []
    residential = _residential_url()
    if residential:
        routes.append(("residential", residential))
    routes.append(("direct", ""))
    if _tunnel_is_up():
        routes.append(("tunnel", DEFAULT_PROXY_URL))
    return routes


def proxy_url() -> str:
    """The first-choice proxy, or "" for a direct connection."""
    return proxy_routes()[0][1]


def proxy_settings() -> dict[str, str] | None:
    """Return a requests-style proxies dict, or None for a direct connection."""
    url = proxy_url()
    return {"http": url, "https": url} if url else None


def proxy_hint() -> str:
    """Explain the proxy in use, for error messages."""
    name, url = proxy_routes()[0]
    if not url:
        return " (connecting directly — no residential creds file, no tunnel)"
    return f" (via {name} route {_redact(url)})"


def _redact(url: str) -> str:
    """Strip credentials out of a proxy URL before it lands in an error."""
    if "@" in url:
        scheme, _, rest = url.partition("://")
        return f"{scheme}://…@{rest.rsplit('@', 1)[-1]}"
    return url
