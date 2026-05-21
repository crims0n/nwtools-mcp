"""Pure IPv4 subnet and address calculation helpers."""

import ipaddress


def _net(cidr: str) -> ipaddress.IPv4Network:
    return ipaddress.IPv4Network(cidr, strict=False)


def _addr(ip: str) -> ipaddress.IPv4Address:
    return ipaddress.IPv4Address(ip)


def parse_cidr(cidr: str) -> dict:
    """Parse a CIDR block and return key network properties."""
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


def ip_in_subnet(ip: str, cidr: str) -> dict:
    """Check whether an IPv4 address falls within a subnet."""
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


def subnets_overlap(cidr_a: str, cidr_b: str) -> dict:
    """Check whether two IPv4 subnets overlap."""
    a = _net(cidr_a)
    b = _net(cidr_b)
    overlaps = a.overlaps(b)

    intersection = []
    if overlaps:
        if a.subnet_of(b):
            intersection = [str(a)]
        elif b.subnet_of(a):
            intersection = [str(b)]
        else:
            start = max(a.network_address, b.network_address)
            end = min(a.broadcast_address, b.broadcast_address)
            intersection = [str(n) for n in ipaddress.summarize_address_range(start, end)]

    return {
        "subnet_a": str(a),
        "subnet_b": str(b),
        "overlaps": overlaps,
        "intersection": intersection,
    }


def cidr_to_range(cidr: str) -> dict:
    """Convert a CIDR block to its first and last IP address."""
    net = _net(cidr)
    return {
        "cidr": str(net),
        "first_address": str(net.network_address),
        "last_address": str(net.broadcast_address),
    }


def range_to_cidrs(first_ip: str, last_ip: str) -> dict:
    """Convert an inclusive IP address range to the minimal list of covering CIDRs."""
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


def subtract_subnet(base_cidr: str, remove_cidr: str) -> dict:
    """Subtract one subnet from another and return the remaining address space as CIDRs."""
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


def find_gaps(container_cidr: str, used_cidrs: list[str]) -> dict:
    """Find unallocated address space within a container block."""
    container = _net(container_cidr)
    used = []
    for c in used_cidrs:
        net = _net(c)
        if not net.subnet_of(container):
            raise ValueError(f"{c} is not within {container_cidr}")
        used.append(net)

    used_collapsed = list(ipaddress.collapse_addresses(used))
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


def check_coverage(target_cidr: str, covering_cidrs: list[str]) -> dict:
    """Check whether a set of CIDRs fully covers a target block."""
    target = _net(target_cidr)
    covering = []
    outside = []
    for c in covering_cidrs:
        net = _net(c)
        if net.overlaps(target):
            start = max(net.network_address, target.network_address)
            end = min(net.broadcast_address, target.broadcast_address)
            clipped = list(ipaddress.summarize_address_range(start, end))
            covering.extend(clipped)
        else:
            outside.append(str(net))

    collapsed = list(ipaddress.collapse_addresses(covering))
    gaps = []
    cursor = int(target.network_address)
    target_end = int(target.broadcast_address)

    for net in sorted(collapsed, key=lambda n: n.network_address):
        net_start = int(net.network_address)
        if cursor < net_start:
            gaps.extend(
                ipaddress.summarize_address_range(
                    ipaddress.IPv4Address(cursor),
                    ipaddress.IPv4Address(net_start - 1),
                )
            )
        cursor = max(cursor, int(net.broadcast_address) + 1)

    if cursor <= target_end:
        gaps.extend(
            ipaddress.summarize_address_range(
                ipaddress.IPv4Address(cursor),
                ipaddress.IPv4Address(target_end),
            )
        )

    return {
        "target": str(target),
        "fully_covered": len(gaps) == 0,
        "gaps": [str(g) for g in gaps],
        "outside_target": outside,
    }


def summarize_cidrs(cidrs: list[str]) -> dict:
    """Collapse a list of CIDRs into the minimal set of covering supernets."""
    nets = [_net(c) for c in cidrs]
    collapsed = list(ipaddress.collapse_addresses(nets))
    return {
        "input_count": len(cidrs),
        "summarized": [str(n) for n in collapsed],
        "summarized_count": len(collapsed),
    }


_CLASSIFICATIONS = [
    ("loopback", lambda a: a.is_loopback),
    ("link_local", lambda a: a.is_link_local),
    ("multicast", lambda a: a.is_multicast),
    ("private", lambda a: a.is_private),
    ("public", lambda a: a.is_global),
    ("unspecified", lambda a: a.is_unspecified),
    ("reserved", lambda a: a.is_reserved),
]

_RFC1918 = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]


def classify_ip(ip: str) -> dict:
    """Classify an IPv4 address by its scope and allocation type."""
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


def ip_convert(ip: str) -> dict:
    """Convert an IPv4 address between dotted-decimal, hex, binary, and integer forms."""
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
