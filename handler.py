"""
Drop-in logging.Handler — plugs into Python's standard logging.

Usage:
    import logging
    from tb_loki_central_logger import LokiHandler

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = LokiHandler(
        url="https://logs-prod-036.grafana.net",
        labels={"service": "my-app", "env": "dev", "request_id": "req_abc123"},
    )
    handler.setLevel(logging.INFO)

    root_logger.addHandler(handler)

    # Now all your existing logging calls go to Loki automatically
    logging.info("Hello World")
    logging.error("Something broke")
"""

import logging
import queue
import threading
from typing import Optional

from .client import LokiClient


# Map Python log level names to lowercase strings for Loki labels
_LEVEL_MAP = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warn",
    "ERROR": "error",
    "CRITICAL": "critical",
}


class LokiHandler(logging.Handler):
    """
    A logging.Handler that ships records to Loki asynchronously.
    Uses a background thread + queue so it never blocks your app.

    Args:
        url:         Loki URL (host or full ``.../loki/api/v1/push``; default from env / ``LokiClient``)
        labels:      Static labels added to every log line
        timeout:     HTTP timeout in seconds (default: 5)
        queue_size:  Max buffered records before dropping (default: 1000)
        basic_auth:  Optional ``(username, token)`` for HTTP Basic auth (Grafana Cloud Loki).
    """

    def __init__(
        self,
        url: Optional[str] = None,
        labels: Optional[dict] = None,
        timeout: int = 5,
        queue_size: int = 1000,
        basic_auth: Optional[tuple[str, str]] = None,
    ):
        super().__init__()
        self._client = LokiClient(
            url=url, labels=labels, timeout=timeout, basic_auth=basic_auth
        )
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="loki-handler")
        self._thread.start()

    # ── Internal worker ───────────────────────────────────────────────────────

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=0.5)
                self._ship(record)
                self._queue.task_done()
            except queue.Empty:
                continue

    def _ship(self, record: logging.LogRecord):
        level = _LEVEL_MAP.get(record.levelname, "info")
        message = self.format(record)
        self._client.push(message, level=level, labels={"logger": record.name})

    # ── logging.Handler interface ─────────────────────────────────────────────

    def emit(self, record: logging.LogRecord):
        try:
            self._queue.put_nowait(record)
        except queue.Full:
            pass  # Drop silently — never crash the caller

    def close(self):
        """Flush remaining records and stop the background thread."""
        self._stop_event.set()
        self._thread.join(timeout=5)
        # Drain anything left in the queue
        while not self._queue.empty():
            try:
                self._ship(self._queue.get_nowait())
            except queue.Empty:
                break
        super().close()
