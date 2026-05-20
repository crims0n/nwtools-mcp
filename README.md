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

## Local use (stdio)

The stdio transport is used when Claude Desktop spawns the server as a subprocess. No network port is opened.

Install and run directly:

```bash
pip install -e .
python server.py
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
      "args": ["/path/to/nwtools-mcp/server.py"]
    }
  }
}
```

Or with Docker:

```json
{
  "mcpServers": {
    "nwtools": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "nwtools-mcp"]
    }
  }
}
```

## Remote deployment (HTTP)

The server supports `streamable-http` (recommended) and `sse` transports for remote access. Set `MCP_TRANSPORT` to switch modes.

### Running the HTTP server

```bash
# Local test
MCP_TRANSPORT=streamable-http python server.py

# With auth
API_KEY=your-secret MCP_TRANSPORT=streamable-http python server.py
```

With Docker:

```bash
docker build -t nwtools-mcp .
docker run --rm -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  -e API_KEY=your-secret \
  nwtools-mcp
```

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

## Requirements

- Python 3.11+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk) — all other dependencies (`uvicorn`, `starlette`) are pulled in transitively
