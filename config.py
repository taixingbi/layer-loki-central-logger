"""
Environment variable names, defaults, and ``.env`` loading for Grafana Cloud Loki.

Keys merged from ``.env`` (current working directory on import) when not already set::

    GRAFANA_CLOUD_URL
    GRAFANA_CLOUD_USER
    GRAFANA_CLOUD_WRITE_API_KEY   # preferred for Loki push (Grafana Cloud write token)
    GRAFANA_CLOUD_API_KEY         # legacy alias

Defaults apply when the matching env var is unset: :data:`DEFAULT_LOKI_URL`,
:data:`DEFAULT_LOKI_URL_USER` (stack / tenant id string for Basic auth username).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final, Optional

DEFAULT_LOKI_URL: Final = "https://logs-prod-036.grafana.net/loki/api/v1/push"
DEFAULT_LOKI_URL_USER: Final = (
    "1529533"  # Grafana Cloud user / tenant id (Basic auth username)
)

ENV_GRAFANA_CLOUD_URL: Final = "GRAFANA_CLOUD_URL"
ENV_GRAFANA_CLOUD_USER: Final = "GRAFANA_CLOUD_USER"
ENV_GRAFANA_CLOUD_WRITE_API_KEY: Final = "GRAFANA_CLOUD_WRITE_API_KEY"


def load_dotenv(path: Path) -> None:
    """Populate ``os.environ`` from a ``.env`` file; never overrides existing keys."""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue

        value = value.strip().strip("'").strip('"')
        if key not in os.environ:
            os.environ[key] = value


def load_dotenv_cwd(filename: str = ".env") -> None:
    """Load .env from the current working directory."""
    load_dotenv(Path.cwd() / filename)


def loki_url_from_env() -> str:
    """
    Read Loki base/push URL from env.

    Accepts either:
    - https://logs-prod-XXX.grafana.net
    - https://logs-prod-XXX.grafana.net/loki/api/v1/push
    """
    return os.environ.get(ENV_GRAFANA_CLOUD_URL, "").strip() or DEFAULT_LOKI_URL


def loki_user_from_env() -> str:
    """
    Basic auth username for Grafana Cloud Loki push.
    Usually this is the Grafana Cloud stack/user/tenant id.
    """
    return os.environ.get(ENV_GRAFANA_CLOUD_USER, "").strip() or DEFAULT_LOKI_URL_USER


def loki_token_from_env() -> Optional[str]:
    """
    Read write-capable token from env.

    Prefers:
    - GRAFANA_CLOUD_WRITE_API_KEY

    Falls back to:
    - GRAFANA_CLOUD_API_KEY
    """
    write_k = os.environ.get(ENV_GRAFANA_CLOUD_WRITE_API_KEY, "").strip()
    if write_k:
        return write_k

    legacy = os.environ.get("GRAFANA_CLOUD_API_KEY", "").strip()
    return legacy or None


def basic_auth_from_env() -> Optional[tuple[str, str]]:
    """Return (username, token) for HTTP Basic auth, or None if token is missing."""
    token = loki_token_from_env()
    if not token:
        return None
    return (loki_user_from_env(), token)


def push_endpoint(url: str) -> str:
    """
    Normalize the Loki push endpoint.
    If caller passes the base host, append /loki/api/v1/push.
    """
    base = url.rstrip("/")
    if base.endswith("/loki/api/v1/push"):
        return base
    return base + "/loki/api/v1/push"


load_dotenv_cwd()