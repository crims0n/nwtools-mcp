# nwtools-mcp

An MCP server that gives LLMs accurate IPv4 subnet and address tools. LLMs are unreliable at network math — this server provides deterministic, correct results via Python's `ipaddress` standard library.

## Tools

| Tool | Description |
|---|---|
| `parse_cidr` | Network address, broadcast, netmask, wildcard mask, host count |
| `ip_in_subnet` | Check whether an IP falls within a subnet |
| `subnets_overlap` | Detect overlap between two subnets and return the intersection |
| `cidr_to_range` | Convert a CIDR to its first and last IP address |
| `range_to_cidrs` | Convert an IP range to the minimal list of covering CIDRs |
| `subtract_subnet` | Carve a subnet out of a larger block, returning remaining CIDRs |
| `find_gaps` | Find unallocated space within a container block |
| `check_coverage` | Check whether a set of CIDRs fully covers a target block |
| `summarize_cidrs` | Collapse a list of CIDRs into the minimal set of supernets |
| `classify_ip` | Classify an IP as RFC 1918, loopback, link-local, multicast, or public |
| `ip_convert` | Convert an IP between dotted-decimal, hex, binary, and integer |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `streamable-http`, or `sse` |
| `HOST` | `0.0.0.0` | Bind address (HTTP transports only) |
| `PORT` | `8000` | Listen port (HTTP transports only) |
| `API_KEY` | _(none)_ | When set, requires `X-API-Key: <value>` on all HTTP requests |
| `LOG_LEVEL` | `INFO` | Python log level for process and request logging |

## Local use (stdio)

The stdio transport is used when Claude Desktop spawns the server as a subprocess. No network port is opened.

### Run from PyPI with uvx

Once published, the simplest way to run the server locally will be:

```bash
uvx nwtools-mcp
```

That runs the `nwtools-mcp` console command from an isolated ephemeral environment. For a persistent install:

```bash
uv tool install nwtools-mcp
nwtools-mcp
```

Install and run directly:

```bash
pip install -e .
python main.py
```

Or use the console script:

```bash
nwtools-mcp
```

Or install from PyPI with pip:

```bash
pip install nwtools-mcp
nwtools-mcp
```

Or via Docker:

```bash
docker run --rm -i nwtools-mcp
```

### Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nwtools": {
      "command": "python",
      "args": ["/path/to/nwtools-mcp/main.py"]
    }
  }
}
```

Or with Docker:

```json
{
  "mcpServers": {
    "nwtools": {
      "command": "uvx",
      "args": ["nwtools-mcp"]
    }
  }
}
```

If you prefer a persistent uv-managed install, use:

```json
{
  "mcpServers": {
    "nwtools": {
      "command": "nwtools-mcp"
    }
  }
}
```

## Remote deployment (HTTP)

The server supports `streamable-http` (recommended) and `sse` transports for remote access. Set `MCP_TRANSPORT` to switch modes.

### Running the HTTP server

```bash
# Local test
MCP_TRANSPORT=streamable-http python main.py

# With auth
API_KEY=your-secret MCP_TRANSPORT=streamable-http python main.py
```

With Docker:

```bash
docker build -t nwtools-mcp .
docker run --rm -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  -e API_KEY=your-secret \
  nwtools-mcp
```

### Operational endpoints

When running in HTTP mode, the container exposes two unauthenticated probe endpoints:

| Endpoint | Description |
|---|---|
| `/healthz` | Basic liveness probe |
| `/readyz` | Readiness probe |

HTTP requests are also logged as structured JSON lines, including method, path, status, duration, client IP, and request ID.

### TLS and auth

The server does not terminate TLS. In production, place it behind a reverse proxy. Example Caddy config:

```
nwtools.example.com {
    reverse_proxy localhost:8000
}
```

The built-in `API_KEY` check adds a layer of defense at the application level, but it does not replace TLS — never expose the server without it.

### Connecting Claude to a remote server

In Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nwtools": {
      "url": "https://nwtools.example.com/mcp",
      "headers": {
        "X-API-Key": "your-secret"
      }
    }
  }
}
```

On claude.ai, add the server under **Settings → Integrations** using the same URL.

## Development

Install with the `test` extra and run the suite:

```bash
pip install -e ".[test]"
pytest
```

To build distribution artifacts locally:

```bash
uv build
```

Or with the standard Python build frontend:

```bash
pip install build
python -m build
```

## Release

The project is now structured to publish cleanly to PyPI and run via `uvx`.

Build locally:

```bash
uv build
```

Publish manually with a token:

```bash
uv publish
```

For GitHub Actions, the repo includes [publish.yml](/Users/patrick/Downloads/nwtools-mcp/.github/workflows/publish.yml) for PyPI Trusted Publishing. Before using it:

1. Create a `pypi` environment in the GitHub repository settings.
2. Add a Trusted Publisher for this project on PyPI that matches:
   `Repository owner`: `crims0n`
   `Repository name`: `nwtools-mcp`
   `Workflow filename`: `publish.yml`
   `Environment name`: `pypi`
3. Push a version tag such as `v0.2.0`.

The publish workflow builds the wheel and sdist, smoke-tests both artifacts, and then runs `uv publish`.

## Requirements

- Python 3.11+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk)
- `uvicorn`
