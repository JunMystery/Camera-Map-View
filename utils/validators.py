"""Validation helpers for user-editable camera data."""

import re


IPV4_PATTERN = re.compile(
    r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)


def is_valid_ipv4(ip_address: str) -> bool:
    """Return whether a string is a valid IPv4 address."""
    return bool(IPV4_PATTERN.fullmatch(ip_address.strip()))


def is_non_empty_text(value: str) -> bool:
    """Return whether text has visible content."""
    return bool(value.strip())
