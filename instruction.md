# tb-loki-central-logger

## Install

```bash
pip install tb-loki-central-logger
```

## Hello World test

Spin up Loki locally first:

```bash
# From the loki-logging/ docker-compose project
docker compose up -d loki

# Then run the test
python hello_world_test.py
```

Open Grafana at **https://logs-prod-036.grafana.net** and query:

```logql
{service="hello-world-test"}
```

---

## API Reference

### `tb_loki_central_logger.configure(url, labels, timeout)`

Configure the module-level default client. Call once at startup.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | str | `https://logs-prod-036.grafana.net` | Loki base URL |
| `labels` | dict | `{}` | Static labels on every log line |
| `timeout` | int | `5` | HTTP timeout in seconds |

### `push_log(message, level, labels)`

Push a single log line.

```python
push_log("Hello", level="info", labels={"request_id": "abc123"})
```

### `push_logs(entries)`

Push a batch of `(message, level)` tuples in one HTTP request.

```python
push_logs([
    ("Started",       "info"),
    ("Config loaded", "info"),
    ("Cache miss",    "warn"),
])
```

### `LokiHandler(url, labels, timeout, queue_size)`

Drop-in `logging.Handler`. Ships records asynchronously in a background thread — never blocks your app.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | str | `https://logs-prod-036.grafana.net` | Loki base URL |
| `labels` | dict | `{}` | Static labels added to every record |
| `timeout` | int | `5` | HTTP timeout in seconds |
| `queue_size` | int | `1000` | Max buffered records before dropping |

### `LokiClient(url, labels, timeout)`

Reusable client instance — useful when you need multiple clients for different services.

```python
from tb_loki_central_logger import LokiClient

client = LokiClient("http://loki:3100", labels={"service": "worker"})
client.push("Job started")
client.push_batch([("Step 1", "info"), ("Step 2", "info")])
```

---

## Log levels

Pass any string as `level`. Recommended values that map to Loki label conventions:

| Value | Use for |
|-------|---------|
| `debug` | Verbose internal state |
| `info` | Normal events (default) |
| `warn` | Unexpected but recoverable |
| `error` | Failures needing attention |
| `critical` | System-level failures |

---

## Publish to PyPI

**One-time setup**

1. Create accounts on [pypi.org](https://pypi.org/account/register/) and (optional) [test.pypi.org](https://test.pypi.org/account/register/).
2. Under **Account settings → API tokens**, create a token scoped to the whole account or to the **`tb-loki-central-logger`** project (after the first upload).
3. When **twine** prompts for credentials, username is `__token__` and the password is the token value (including the `pypi-` prefix).

**Each release**

1. Bump **`version`** in `pyproject.toml`.
2. Use a clean virtualenv (or your dev venv) with current tools:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Build source and wheel (artifacts go in **`dist/`**):

```bash
rm -rf dist/ build/ *.egg-info
python -m build
```

4. Check the artifacts:

```bash
twine check dist/*
```

5. Upload to **TestPyPI** first (optional, recommended):

```bash
twine upload --repository testpypi dist/*
```

Verify: `pip install -i https://test.pypi.org/simple/ tb-loki-central-logger==<your-version>`

6. Upload to **PyPI**:

```bash
twine upload dist/*
```

After a few minutes: `pip install tb-loki-central-logger`

**Notes**

- Do not commit **`dist/`** or `*.egg-info/`; keep them in `.gitignore`.
- For automated publishing, use [trusted publishing](https://docs.pypi.org/trusted-publishers/) from GitHub Actions instead of storing tokens in CI secrets where possible.

---

## Local development install

```bash
git clone https://github.com/your-org/tb-loki-central-logger
cd tb-loki-central-logger
pip install -e .
python hello_world_test.py
```

## get 

https://grafana.com/orgs/taixingbi/hosted-logs/1529533

loki.write "grafanacloud" {
  endpoint {
    url = "https://logs-prod-036.grafana.net/loki/api/v1/push"
    basic_auth {
      username = "1529533"
      password = "<Your Grafana.com API Token>"
    }
  }
}


<Your Grafana.com API Token> from Grafana-write
https://grafana.com/orgs/taixingbi/access-policies

