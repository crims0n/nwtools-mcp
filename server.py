"""Compatibility exports for tool functions and MCP server."""

from app import mcp
from main import run
from tools import (
    check_coverage,
    cidr_to_range,
    classify_ip,
    find_gaps,
    ip_convert,
    ip_in_subnet,
    parse_cidr,
    range_to_cidrs,
    subnets_overlap,
    subtract_subnet,
    summarize_cidrs,
)


if __name__ == "__main__":
    run()
