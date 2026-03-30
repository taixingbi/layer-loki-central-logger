import logging
from pathlib import Path

from tb_loki_central_logger import LokiHandler, basic_auth_from_env, load_dotenv

# Loads .env from cwd (same vars as Grafana Cloud docs in the package)
load_dotenv(Path(".env"))

auth = basic_auth_from_env()
if auth is None:
    raise SystemExit(
        "Missing Loki credentials: set GRAFANA_CLOUD_WRITE_API_KEY (or GRAFANA_CLOUD_API_KEY) "
        "in the environment or .env. Optionally set GRAFANA_CLOUD_USER to your stack user id "
        "(Grafana Cloud → My Account → for API key basic auth)."
    )

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

handler = LokiHandler(
    # url="https://logs-prod-036.grafana.net",
    labels={"service": "my-app", "env": "dev"},
    basic_auth=auth,
)
root_logger.addHandler(handler)

logging.info("Hello World")
logging.warning("Cache miss444")
logging.error("Something broke444")

handler.close()