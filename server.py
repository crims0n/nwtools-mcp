"""Compatibility exports for tool functions and MCP server."""

from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from nwtools_mcp.server import (
    check_coverage,
    cidr_to_range,
    classify_ip,
    find_gaps,
    ip_convert,
    ip_in_subnet,
    mcp,
    parse_cidr,
    range_to_cidrs,
    run,
    subnets_overlap,
    subtract_subnet,
    summarize_cidrs,
)


if __name__ == "__main__":
    run()
