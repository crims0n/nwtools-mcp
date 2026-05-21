"""Basic artifact smoke test used by the publish workflow."""

from nwtools_mcp.server import classify_ip, parse_cidr


def main() -> None:
    cidr = parse_cidr("10.0.0.0/24")
    assert cidr["host_count"] == 254

    ip = classify_ip("10.1.2.3")
    assert ip["rfc1918"] is True
    assert ip["rfc1918_block"] == "10.0.0.0/8"


if __name__ == "__main__":
    main()
