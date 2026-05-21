"""nwtools-mcp package."""

from .server import (
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

__all__ = [
    "check_coverage",
    "cidr_to_range",
    "classify_ip",
    "find_gaps",
    "ip_convert",
    "ip_in_subnet",
    "mcp",
    "parse_cidr",
    "range_to_cidrs",
    "run",
    "subnets_overlap",
    "subtract_subnet",
    "summarize_cidrs",
]
