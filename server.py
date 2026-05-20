"""MCP server providing IPv4 subnet and address tools."""

import ipaddress
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nwtools")


def _net(cidr: str) -> ipaddress.IPv4Network:
    return ipaddress.IPv4Network(cidr, strict=False)


def _addr(ip: str) -> ipaddress.IPv4Address:
    return ipaddress.IPv4Address(ip)


# ---------------------------------------------------------------------------
# Core subnet math
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_cidr(cidr: str) -> dict:
    """Parse a CIDR block and return key network properties.

    Returns network address, broadcast address, prefix length, netmask,
    wildcard mask, first usable host, last usable host, and total host count.
    """
    net = _net(cidr)

    if net.prefixlen == 32:
        first_host = last_host = net.network_address
        host_count = 1
    elif net.prefixlen == 31:
        first_host = net.network_address
        last_host = net.broadcast_address
        host_count = 2
    else:
        first_host = net.network_address + 1
        last_host = net.broadcast_address - 1
        host_count = net.num_addresses - 2

    return {
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
        "prefix_length": net.prefixlen,
        "netmask": str(net.netmask),
        "wildcard_mask": str(net.hostmask),
        "first_host": str(first_host),
        "last_host": str(last_host),
        "host_count": host_count,
        "total_addresses": net.num_addresses,
    }


@mcp.tool()
def ip_in_subnet(ip: str, cidr: str) -> dict:
    """Check whether an IPv4 address falls within a subnet.

    Returns a boolean result and the subnet's network/broadcast boundaries
    for confirmation.
    """
    addr = _addr(ip)
    net = _net(cidr)
    contained = addr in net
    return {
        "ip": str(addr),
        "subnet": str(net),
        "contained": contained,
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
    }


@mcp.tool()
def subnets_overlap(cidr_a: str, cidr_b: str) -> dict:
    """Check whether two IPv4 subnets overlap.

    Returns a boolean and, when they do overlap, the intersection as a list
    of CIDRs representing the common address space.
    """
    a = _net(cidr_a)
    b = _net(cidr_b)
    overlaps = a.overlaps(b)

    intersection = []
    if overlaps:
        # The intersection is whichever network is the subset, or their overlap
        if a.subnet_of(b):
            intersection = [str(a)]
        elif b.subnet_of(a):
            intersection = [str(b)]
        else:
            # Partial overlap: find common range
            start = max(a.network_address, b.network_address)
            end = min(a.broadcast_address, b.broadcast_address)
            intersection = [str(n) for n in ipaddress.summarize_address_range(start, end)]

    return {
        "subnet_a": str(a),
        "subnet_b": str(b),
        "overlaps": overlaps,
        "intersection": intersection,
    }


# ---------------------------------------------------------------------------
# Range / set operations
# ---------------------------------------------------------------------------

@mcp.tool()
def cidr_to_range(cidr: str) -> dict:
    """Convert a CIDR block to its first and last IP address (inclusive range)."""
    net = _net(cidr)
    return {
        "cidr": str(net),
        "first_address": str(net.network_address),
        "last_address": str(net.broadcast_address),
    }


@mcp.tool()
def range_to_cidrs(first_ip: str, last_ip: str) -> dict:
    """Convert an inclusive IP address range to the minimal list of CIDRs that cover it exactly."""
    start = _addr(first_ip)
    end = _addr(last_ip)
    if int(start) > int(end):
        raise ValueError(f"first_ip {first_ip} must be <= last_ip {last_ip}")
    cidrs = [str(n) for n in ipaddress.summarize_address_range(start, end)]
    return {
        "first_address": str(start),
        "last_address": str(end),
        "cidrs": cidrs,
        "cidr_count": len(cidrs),
    }


@mcp.tool()
def subtract_subnet(base_cidr: str, remove_cidr: str) -> dict:
    """Subtract one subnet from another and return the remaining address space as CIDRs.

    Useful for carving out a reservation from a larger block.
    Returns the CIDRs that represent base_cidr minus remove_cidr.
    """
    base = _net(base_cidr)
    remove = _net(remove_cidr)

    if not remove.subnet_of(base):
        raise ValueError(f"{remove_cidr} is not a subset of {base_cidr}")

    remaining = list(base.address_exclude(remove))
    return {
        "base": str(base),
        "removed": str(remove),
        "remaining": [str(n) for n in sorted(remaining, key=lambda n: n.network_address)],
        "remaining_host_count": sum(n.num_addresses for n in remaining),
    }


@mcp.tool()
def find_gaps(container_cidr: str, used_cidrs: list[str]) -> dict:
    """Find unallocated address space within a container block.

    Given a container CIDR and a list of allocated subnets within it, returns
    the CIDRs that represent the unused address space.
    """
    container = _net(container_cidr)
    used = []
    for c in used_cidrs:
        net = _net(c)
        if not net.subnet_of(container):
            raise ValueError(f"{c} is not within {container_cidr}")
        used.append(net)

    # Collapse and sort the used networks
    used_collapsed = list(ipaddress.collapse_addresses(used))

    # Walk the container range and collect gaps
    gaps = []
    cursor = int(container.network_address)
    container_end = int(container.broadcast_address)

    for net in sorted(used_collapsed, key=lambda n: n.network_address):
        net_start = int(net.network_address)
        if cursor < net_start:
            gap_cidrs = ipaddress.summarize_address_range(
                ipaddress.IPv4Address(cursor),
                ipaddress.IPv4Address(net_start - 1),
            )
            gaps.extend(gap_cidrs)
        cursor = max(cursor, int(net.broadcast_address) + 1)

    if cursor <= container_end:
        gap_cidrs = ipaddress.summarize_address_range(
            ipaddress.IPv4Address(cursor),
            ipaddress.IPv4Address(container_end),
        )
        gaps.extend(gap_cidrs)

    return {
        "container": str(container),
        "used": [str(n) for n in used_collapsed],
        "gaps": [str(g) for g in gaps],
        "gap_address_count": sum(g.num_addresses for g in gaps),
    }


@mcp.tool()
def check_coverage(target_cidr: str, covering_cidrs: list[str]) -> dict:
    """Check whether a set of CIDRs fully covers a target block.

    Returns whether coverage is complete, any gaps (uncovered ranges as CIDRs),
    and any provided CIDRs that fall outside the target.
    """
    target = _net(target_cidr)
    covering = []
    outside = []
    for c in covering_cidrs:
        net = _net(c)
        if net.overlaps(target):
            # Clip to target boundary
            start = max(net.network_address, target.network_address)
            end = min(net.broadcast_address, target.broadcast_address)
            clipped = list(ipaddress.summarize_address_range(start, end))
            covering.extend(clipped)
        else:
            outside.append(str(net))

    collapsed = list(ipaddress.collapse_addresses(covering))

    # Find gaps within target not covered by collapsed
    gaps = []
    cursor = int(target.network_address)
    target_end = int(target.broadcast_address)

    for net in sorted(collapsed, key=lambda n: n.network_address):
        net_start = int(net.network_address)
        if cursor < net_start:
            gaps.extend(ipaddress.summarize_address_range(
                ipaddress.IPv4Address(cursor),
                ipaddress.IPv4Address(net_start - 1),
            ))
        cursor = max(cursor, int(net.broadcast_address) + 1)

    if cursor <= target_end:
        gaps.extend(ipaddress.summarize_address_range(
            ipaddress.IPv4Address(cursor),
            ipaddress.IPv4Address(target_end),
        ))

    return {
        "target": str(target),
        "fully_covered": len(gaps) == 0,
        "gaps": [str(g) for g in gaps],
        "outside_target": outside,
    }


@mcp.tool()
def summarize_cidrs(cidrs: list[str]) -> dict:
    """Collapse and summarize a list of CIDRs into the minimal set of covering supernets.

    Merges adjacent and overlapping subnets into the fewest possible CIDRs.
    """
    nets = [_net(c) for c in cidrs]
    collapsed = list(ipaddress.collapse_addresses(nets))
    return {
        "input_count": len(cidrs),
        "summarized": [str(n) for n in collapsed],
        "summarized_count": len(collapsed),
    }


# ---------------------------------------------------------------------------
# Address classification
# ---------------------------------------------------------------------------

_CLASSIFICATIONS = [
    ("loopback",    lambda a: a.is_loopback),
    ("link_local",  lambda a: a.is_link_local),
    ("multicast",   lambda a: a.is_multicast),
    ("private",     lambda a: a.is_private),
    ("public",      lambda a: a.is_global),
    ("unspecified", lambda a: a.is_unspecified),
    ("reserved",    lambda a: a.is_reserved),
]

# RFC 1918 ranges explicitly, since is_private includes link-local in Python
_RFC1918 = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]


@mcp.tool()
def classify_ip(ip: str) -> dict:
    """Classify an IPv4 address by its scope and allocation type.

    Returns flags for: rfc1918 private, loopback, link-local, multicast,
    public/global, reserved, and unspecified. Also identifies the RFC 1918
    block the address belongs to if applicable.
    """
    addr = _addr(ip)
    tags = {name: check(addr) for name, check in _CLASSIFICATIONS}

    rfc1918_block = None
    for block in _RFC1918:
        if addr in block:
            rfc1918_block = str(block)
            break

    tags["rfc1918"] = rfc1918_block is not None
    tags["rfc1918_block"] = rfc1918_block

    return {"ip": str(addr), **tags}


# ---------------------------------------------------------------------------
# Address format conversion
# ---------------------------------------------------------------------------

@mcp.tool()
def ip_convert(ip: str) -> dict:
    """Convert an IPv4 address between dotted-decimal, hexadecimal, binary, and integer forms.

    Accepts dotted-decimal (e.g. 192.168.1.1), hex (e.g. 0xC0A80101),
    or integer input.
    """
    # Accept hex or integer strings in addition to dotted-decimal
    if ip.startswith("0x") or ip.startswith("0X"):
        addr = ipaddress.IPv4Address(int(ip, 16))
    elif ip.isdigit():
        addr = ipaddress.IPv4Address(int(ip))
    else:
        addr = _addr(ip)

    n = int(addr)
    octets = str(addr).split(".")
    binary_octets = ".".join(f"{int(o):08b}" for o in octets)

    return {
        "dotted_decimal": str(addr),
        "hexadecimal": f"0x{n:08X}",
        "binary": binary_octets,
        "integer": n,
    }


if __name__ == "__main__":
    import os

    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport in ("streamable-http", "sse"):
        import uvicorn
        from starlette.responses import Response as HttpResponse

        api_key = os.getenv("API_KEY")
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))

        base_app = (
            mcp.streamable_http_app() if transport == "streamable-http" else mcp.sse_app()
        )

        if api_key:
            async def app(scope, receive, send):
                if scope["type"] == "http":
                    headers = dict(scope.get("headers", []))
                    if headers.get(b"x-api-key", b"").decode() != api_key:
                        await HttpResponse("Unauthorized", status_code=401)(scope, receive, send)
                        return
                await base_app(scope, receive, send)
        else:
            app = base_app

        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()
