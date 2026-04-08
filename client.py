"""
Simple push interface — use push_log() for quick one-liners,
or LokiClient for a reusable configured instance.

On first import of :mod:`tb_loki_central_logger.config`, reads ``.env`` from the
current working directory (without overriding existing environment variables).
"""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from .config import basic_auth_from_env, loki_url_from_env, push_endpoint


def _auth_header(basic_auth: Optional[tuple[str, str]]) -> dict[str, str]:
    if not basic_auth:
        return {}
    user, token = basic_auth
    token_b = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token_b}"}


class LokiClient:
    """
    Reusable Loki push client.

    Usage:
        client = LokiClient(
            "https://logs-prod-036.grafana.net/loki/api/v1/push",
            labels={"service": "my-app"},
        )
        client.push("Hello World")
        client.push("Something failed", level="error")
    """

    def __init__(
        self,
        url: Optional[str] = None,
        labels: Optional[dict[str, Any]] = None,
        timeout: int = 5,
        basic_auth: Optional[tuple[str, str]] = None,
    ):
        if url is None:
            url = loki_url_from_env()
        if basic_auth is None:
            basic_auth = basic_auth_from_env()

        self.endpoint = push_endpoint(url)
        self.default_labels = dict(labels) if labels else {}
        self.timeout = timeout
        self._basic_auth = basic_auth
        self._lock = threading.Lock()
        self._http_headers = {
            "Content-Type": "application/json",
            **_auth_header(basic_auth),
        }

    def _send(self, body: bytes) -> None:
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=self._http_headers,
            method="POST",
        )

        with self._lock:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp.read()
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Loki push failed: HTTP {e.code} {e.reason}. Response: {detail}"
                ) from e
            except urllib.error.URLError as e:
                raise RuntimeError(f"Loki push failed: {e}") from e

    def push(
        self,
        message: str,
        level: str = "info",
        labels: Optional[dict[str, Any]] = None,
    ) -> None:
        """Push a single log line to Loki."""
        merged = {**self.default_labels, "level": level}
        if labels:
            merged.update(labels)

        body = json.dumps(
            {
                "streams": [
                    {
                        "stream": merged,
                        "values": [[str(int(time.time() * 1e9)), message]],
                    }
                ]
            }
        ).encode("utf-8")

        self._send(body)

    def push_batch(self, entries: list[tuple[str, str]]) -> None:
        """
        Push multiple entries at once.

        entries = [("message", "level"), ...]
        """
        streams: dict[str, dict[str, Any]] = {}

        for message, level in entries:
            label = {**self.default_labels, "level": level}
            label_key = json.dumps(label, sort_keys=True)

            if label_key not in streams:
                streams[label_key] = {"stream": label, "values": []}

            streams[label_key]["values"].append(
                [str(int(time.time() * 1e9)), message]
            )

        body = json.dumps({"streams": list(streams.values())}).encode("utf-8")
        self._send(body)


_default_client: Optional[LokiClient] = None


def configure(
    url: Optional[str] = None,
    labels: Optional[dict[str, Any]] = None,
    timeout: int = 5,
    basic_auth: Optional[tuple[str, str]] = None,
) -> None:
    """
    Configure the module-level default client.
    Call once at startup.

    Omit ``url`` / ``basic_auth`` to take them from the environment (optionally
    via a ``.env`` file): ``GRAFANA_CLOUD_URL``, ``GRAFANA_CLOUD_USER``,
    ``GRAFANA_CLOUD_WRITE_API_KEY`` (or legacy ``GRAFANA_CLOUD_API_KEY``).

    Matches Grafana Cloud Loki basic auth:
    - username = Cloud stack / tenant id
    - password = API token

    ``url`` may be either the Loki host or the full push path.

        import tb_loki_central_logger
        tb_loki_central_logger.configure(labels={"service": "my-app"})
    """
    global _default_client
    _default_client = LokiClient(
        url=url,
        labels=labels,
        timeout=timeout,
        basic_auth=basic_auth,
    )


def _get_client() -> LokiClient:
    global _default_client
    if _default_client is None:
        _default_client = LokiClient()
    return _default_client


def push_log(
    message: str,
    level: str = "info",
    labels: Optional[dict[str, Any]] = None,
) -> None:
    """
    Push a single log line using the default client.

        from tb_loki_central_logger import push_log
        push_log("Hello World")
        push_log("Something failed", level="error")
    """
    _get_client().push(message, level=level, labels=labels)


def push_logs(entries: list[tuple[str, str]]) -> None:
    """
    Push multiple log lines at once.

        from tb_loki_central_logger import push_logs
        push_logs([("Started", "info"), ("Loaded config", "info")])
    """
    _get_client().push_batch(entries)