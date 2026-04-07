import asyncio
import logging

from tb_loki_central_logger import LokiHandler, basic_auth_from_env
from tb_loki_central_logger import configure, push_log

# import loads .env from cwd — run: python test.py from repo root

auth = basic_auth_from_env()
if auth is None:
    raise SystemExit(
        "Missing Loki credentials in .env / env: set GRAFANA_CLOUD_URL, GRAFANA_CLOUD_USER, "
        "and GRAFANA_CLOUD_API_KEY (or legacy GRAFANA_CLOUD_WRITE_API_KEY)."
    )

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = LokiHandler(
    labels={"service": "my-app", "env": "dev"},
    basic_auth=auth,
)
root_logger.addHandler(handler)

logging.info("Hello World")
logging.warning("Cache miss")
logging.error("Something broke")

handler.close()


async def _async_demo():
    await configure(labels={"service": "my-app", "env": "dev"}, basic_auth=auth)
    await push_log("direct async push_log()", level="info")


asyncio.run(_async_demo())
