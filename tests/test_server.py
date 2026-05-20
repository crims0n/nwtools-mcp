"""Tests for the nwtools-mcp tool functions.

Tools are imported and called directly as plain Python functions.
The MCP protocol layer is not exercised here — these tests verify
that the network math underlying each tool is correct.
"""

import pytest

from server import (
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


# ---------------------------------------------------------------------------
# parse_cidr
# ---------------------------------------------------------------------------

class TestParseCidr:
    def test_slash_24(self):
        r = parse_cidr("192.168.1.0/24")
        assert r["network_address"] == "192.168.1.0"
        assert r["broadcast_address"] == "192.168.1.255"
        assert r["prefix_length"] == 24
        assert r["netmask"] == "255.255.255.0"
        assert r["wildcard_mask"] == "0.0.0.255"
        assert r["first_host"] == "192.168.1.1"
        assert r["last_host"] == "192.168.1.254"
        assert r["host_count"] == 254
        assert r["total_addresses"] == 256

    def test_slash_30(self):
        r = parse_cidr("10.0.0.0/30")
        assert r["host_count"] == 2
        assert r["total_addresses"] == 4
        assert r["first_host"] == "10.0.0.1"
        assert r["last_host"] == "10.0.0.2"

    def test_slash_31_rfc3021(self):
        # /31 point-to-point: both addresses are usable
        r = parse_cidr("10.0.0.0/31")
        assert r["host_count"] == 2
        assert r["total_addresses"] == 2

    def test_slash_32_single_host(self):
        r = parse_cidr("10.0.0.5/32")
        assert r["host_count"] == 1
        assert r["total_addresses"] == 1
        assert r["first_host"] == "10.0.0.5"
        assert r["last_host"] == "10.0.0.5"

    def test_host_bits_set_is_accepted(self):
        # strict=False: input with host bits set is normalized
        r = parse_cidr("192.168.1.42/24")
        assert r["network_address"] == "192.168.1.0"
        assert r["broadcast_address"] == "192.168.1.255"


# ---------------------------------------------------------------------------
# ip_in_subnet
# ---------------------------------------------------------------------------

class TestIpInSubnet:
    @pytest.mark.parametrize("ip,cidr,expected", [
        ("192.168.1.50", "192.168.1.0/24", True),
        ("192.168.2.1", "192.168.1.0/24", False),
        ("192.168.1.0", "192.168.1.0/24", True),    # network address
        ("192.168.1.255", "192.168.1.0/24", True),  # broadcast address
        ("10.0.0.1", "10.0.0.0/8", True),
        ("11.0.0.1", "10.0.0.0/8", False),
    ])
    def test_membership(self, ip, cidr, expected):
        assert ip_in_subnet(ip, cidr)["contained"] is expected


# ---------------------------------------------------------------------------
# subnets_overlap
# ---------------------------------------------------------------------------

class TestSubnetsOverlap:
    def test_disjoint(self):
        r = subnets_overlap("10.0.0.0/24", "10.0.1.0/24")
        assert r["overlaps"] is False
        assert r["intersection"] == []

    def test_subset(self):
        r = subnets_overlap("10.0.0.0/25", "10.0.0.0/24")
        assert r["overlaps"] is True
        assert r["intersection"] == ["10.0.0.0/25"]

    def test_supernet(self):
        r = subnets_overlap("10.0.0.0/24", "10.0.0.0/25")
        assert r["overlaps"] is True
        assert r["intersection"] == ["10.0.0.0/25"]

    def test_identical(self):
        r = subnets_overlap("10.0.0.0/24", "10.0.0.0/24")
        assert r["overlaps"] is True
        assert r["intersection"] == ["10.0.0.0/24"]


# ---------------------------------------------------------------------------
# cidr_to_range
# ---------------------------------------------------------------------------

class TestCidrToRange:
    def test_slash_24(self):
        r = cidr_to_range("192.168.1.0/24")
        assert r["first_address"] == "192.168.1.0"
        assert r["last_address"] == "192.168.1.255"

    def test_slash_32(self):
        r = cidr_to_range("10.0.0.5/32")
        assert r["first_address"] == "10.0.0.5"
        assert r["last_address"] == "10.0.0.5"


# ---------------------------------------------------------------------------
# range_to_cidrs
# ---------------------------------------------------------------------------

class TestRangeToCidrs:
    def test_aligned_range_is_single_cidr(self):
        r = range_to_cidrs("10.0.0.0", "10.0.0.255")
        assert r["cidrs"] == ["10.0.0.0/24"]
        assert r["cidr_count"] == 1

    def test_unaligned_range_splits(self):
        r = range_to_cidrs("10.0.0.1", "10.0.0.6")
        assert r["cidrs"] == [
            "10.0.0.1/32",
            "10.0.0.2/31",
            "10.0.0.4/31",
            "10.0.0.6/32",
        ]
        assert r["cidr_count"] == 4

    def test_first_greater_than_last_raises(self):
        with pytest.raises(ValueError):
            range_to_cidrs("10.0.0.10", "10.0.0.1")


# ---------------------------------------------------------------------------
# subtract_subnet
# ---------------------------------------------------------------------------

class TestSubtractSubnet:
    def test_carve_middle(self):
        r = subtract_subnet("10.0.0.0/24", "10.0.0.128/25")
        assert r["remaining"] == ["10.0.0.0/25"]
        assert r["remaining_host_count"] == 128

    def test_carve_small_block(self):
        r = subtract_subnet("10.0.0.0/24", "10.0.0.64/26")
        # Remaining: 10.0.0.0/26 + 10.0.0.128/25
        assert r["remaining"] == ["10.0.0.0/26", "10.0.0.128/25"]

    def test_non_subset_raises(self):
        with pytest.raises(ValueError):
            subtract_subnet("10.0.0.0/24", "10.0.1.0/24")


# ---------------------------------------------------------------------------
# find_gaps
# ---------------------------------------------------------------------------

class TestFindGaps:
    def test_no_used_returns_full_container(self):
        r = find_gaps("10.0.0.0/24", [])
        assert r["gaps"] == ["10.0.0.0/24"]
        assert r["gap_address_count"] == 256

    def test_middle_gap(self):
        # Used: 10.0.0.0/26 and 10.0.0.192/26
        # Gap:  10.0.0.64/26 and 10.0.0.128/26
        r = find_gaps("10.0.0.0/24", ["10.0.0.0/26", "10.0.0.192/26"])
        assert r["gaps"] == ["10.0.0.64/26", "10.0.0.128/26"]
        assert r["gap_address_count"] == 128

    def test_fully_used_no_gaps(self):
        r = find_gaps("10.0.0.0/24", ["10.0.0.0/25", "10.0.0.128/25"])
        assert r["gaps"] == []
        assert r["gap_address_count"] == 0

    def test_used_outside_container_raises(self):
        with pytest.raises(ValueError):
            find_gaps("10.0.0.0/24", ["10.0.1.0/26"])


# ---------------------------------------------------------------------------
# check_coverage
# ---------------------------------------------------------------------------

class TestCheckCoverage:
    def test_full_coverage(self):
        r = check_coverage("10.0.0.0/24", ["10.0.0.0/25", "10.0.0.128/25"])
        assert r["fully_covered"] is True
        assert r["gaps"] == []
        assert r["outside_target"] == []

    def test_partial_coverage(self):
        r = check_coverage("10.0.0.0/24", ["10.0.0.0/25"])
        assert r["fully_covered"] is False
        assert r["gaps"] == ["10.0.0.128/25"]

    def test_outside_cidrs_are_reported(self):
        r = check_coverage(
            "10.0.0.0/24",
            ["10.0.0.0/24", "192.168.1.0/24"],
        )
        assert r["fully_covered"] is True
        assert r["outside_target"] == ["192.168.1.0/24"]

    def test_covering_supernet_is_clipped_to_target(self):
        # A /16 covers our /24 — should be clipped, not flagged as outside.
        r = check_coverage("10.0.5.0/24", ["10.0.0.0/16"])
        assert r["fully_covered"] is True
        assert r["outside_target"] == []


# ---------------------------------------------------------------------------
# summarize_cidrs
# ---------------------------------------------------------------------------

class TestSummarizeCidrs:
    def test_adjacent_collapses(self):
        r = summarize_cidrs(["10.0.0.0/25", "10.0.0.128/25"])
        assert r["summarized"] == ["10.0.0.0/24"]
        assert r["summarized_count"] == 1

    def test_overlapping_collapses(self):
        r = summarize_cidrs(["10.0.0.0/24", "10.0.0.0/25"])
        assert r["summarized"] == ["10.0.0.0/24"]

    def test_non_adjacent_stays_separate(self):
        r = summarize_cidrs(["10.0.0.0/24", "10.0.2.0/24"])
        assert r["summarized_count"] == 2


# ---------------------------------------------------------------------------
# classify_ip
# ---------------------------------------------------------------------------

class TestClassifyIp:
    def test_rfc1918_class_a(self):
        r = classify_ip("10.5.5.5")
        assert r["rfc1918"] is True
        assert r["rfc1918_block"] == "10.0.0.0/8"
        assert r["private"] is True
        assert r["public"] is False

    def test_rfc1918_class_b(self):
        r = classify_ip("172.16.0.1")
        assert r["rfc1918"] is True
        assert r["rfc1918_block"] == "172.16.0.0/12"

    def test_rfc1918_class_c(self):
        r = classify_ip("192.168.1.1")
        assert r["rfc1918"] is True
        assert r["rfc1918_block"] == "192.168.0.0/16"

    def test_loopback(self):
        r = classify_ip("127.0.0.1")
        assert r["loopback"] is True
        assert r["rfc1918"] is False

    def test_link_local(self):
        r = classify_ip("169.254.1.1")
        assert r["link_local"] is True
        # is_private in Python includes link-local — rfc1918 should not
        assert r["rfc1918"] is False

    def test_multicast(self):
        r = classify_ip("224.0.0.1")
        assert r["multicast"] is True

    def test_public(self):
        r = classify_ip("8.8.8.8")
        assert r["public"] is True
        assert r["rfc1918"] is False
        assert r["private"] is False


# ---------------------------------------------------------------------------
# ip_convert
# ---------------------------------------------------------------------------

class TestIpConvert:
    def test_from_dotted(self):
        r = ip_convert("192.168.1.1")
        assert r["dotted_decimal"] == "192.168.1.1"
        assert r["hexadecimal"] == "0xC0A80101"
        assert r["binary"] == "11000000.10101000.00000001.00000001"
        assert r["integer"] == 3232235777

    def test_from_hex(self):
        r = ip_convert("0xC0A80101")
        assert r["dotted_decimal"] == "192.168.1.1"

    def test_from_hex_lowercase_prefix(self):
        r = ip_convert("0Xc0a80101")
        assert r["dotted_decimal"] == "192.168.1.1"

    def test_from_integer_string(self):
        r = ip_convert("3232235777")
        assert r["dotted_decimal"] == "192.168.1.1"

    def test_zero_address(self):
        r = ip_convert("0.0.0.0")
        assert r["hexadecimal"] == "0x00000000"
        assert r["binary"] == "00000000.00000000.00000000.00000000"
        assert r["integer"] == 0
