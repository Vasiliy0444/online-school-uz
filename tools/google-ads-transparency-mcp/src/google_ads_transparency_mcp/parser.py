"""Decode text ad content from Google Ads Transparency iframe preview URLs.

Two encodings turn up. The current one is the `overlay=` parameter on
displayads-formats.googleusercontent.com preview URLs: urlsafe base64 wrapping a
gzip stream wrapping protobuf, whose repeated field 9 holds {name, {value}} pairs
with real field names (`headline`, `description`, `visurl`). That is parsed exactly.

The older shape put plain base64 in an `ad=` parameter with no field names, so it
falls back to scraping readable strings out of the bytes and assigning them by
position. Prefer the overlay path; the heuristic is only there for stale URLs.
"""

from __future__ import annotations

import base64
import gzip
import re
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse


def decode_text_ad(iframe_url: str) -> dict[str, str] | None:
    """Extract headline, description, and destination URL from an iframe preview URL.

    Returns None if the URL doesn't contain decodable ad data.
    """
    overlay = _decode_overlay(iframe_url)
    if overlay:
        return overlay

    ad_param = _extract_ad_param(iframe_url)
    if not ad_param:
        return None

    try:
        raw = base64.b64decode(ad_param + "==")  # pad generously
    except Exception:
        return None

    return _parse_ad_bytes(raw)


def _decode_overlay(url: str) -> dict[str, str] | None:
    """Decode the `overlay=` parameter: base64 -> gzip -> protobuf name/value pairs."""
    try:
        values = parse_qs(urlparse(url).query).get("overlay")
        if not values:
            return None
        blob = values[0].lstrip("=")
        packed = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
        fields = _overlay_fields(gzip.decompress(packed))
    except Exception:
        return None

    if not fields:
        return None

    return {
        "headline": fields.get("headline", ""),
        "description": fields.get("description", ""),
        "destination_url": fields.get("visurl", ""),
    }


def _read_varint(data: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while i < len(data):
        byte = data[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7
    raise ValueError("truncated varint")


def _iter_fields(data: bytes) -> Iterator[tuple[int, int, Any]]:
    """Walk one protobuf message, yielding (field_number, wire_type, value)."""
    i = 0
    while i < len(data):
        key, i = _read_varint(data, i)
        field, wire = key >> 3, key & 0x07
        if wire == 0:
            value, i = _read_varint(data, i)
            yield field, wire, value
        elif wire == 2:
            length, i = _read_varint(data, i)
            if i + length > len(data):
                raise ValueError("truncated length-delimited field")
            yield field, wire, data[i : i + length]
            i += length
        elif wire == 5:
            yield field, wire, data[i : i + 4]
            i += 4
        elif wire == 1:
            yield field, wire, data[i : i + 8]
            i += 8
        else:
            raise ValueError(f"unsupported wire type {wire}")


def _overlay_fields(data: bytes) -> dict[str, str]:
    """Pull {name: value} out of the overlay message's repeated field 9."""
    out: dict[str, str] = {}
    for field, wire, value in _iter_fields(data):
        if field != 9 or wire != 2:
            continue
        name = text = ""
        for inner_field, inner_wire, inner in _iter_fields(value):
            if inner_wire != 2:
                continue
            if inner_field == 1:
                name = inner.decode("utf-8", "replace")
            elif inner_field == 2:
                for leaf_field, leaf_wire, leaf in _iter_fields(inner):
                    if leaf_field == 1 and leaf_wire == 2:
                        text = leaf.decode("utf-8", "replace")
                        break
        if name:
            out[name] = text
    return out


def _extract_ad_param(url: str) -> str | None:
    """Pull the `ad=` query parameter from a URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        values = params.get("ad")
        if values:
            return values[0]
    except Exception:
        pass

    # Fallback: regex for ad= in case URL is malformed
    match = re.search(r"[?&]ad=([A-Za-z0-9_+/=-]+)", url)
    return match.group(1) if match else None


def _parse_ad_bytes(data: bytes) -> dict[str, str]:
    """Extract readable text fields from the decoded protobuf-like binary.

    The binary format contains length-prefixed UTF-8 strings with single-byte
    type/field tags before them. We extract all printable strings and map them
    to headline, description, and destination URL by position and content heuristics.
    """
    strings = _extract_strings(data)

    headline = ""
    description = ""
    destination_url = ""

    for s in strings:
        s_stripped = s.strip()
        if not s_stripped:
            continue
        # URL detection
        if _looks_like_url(s_stripped):
            if not destination_url:
                destination_url = s_stripped
        elif not headline:
            headline = s_stripped
        elif not description:
            description = s_stripped

    return {
        "headline": headline,
        "description": description,
        "destination_url": destination_url,
    }


def _extract_strings(data: bytes) -> list[str]:
    """Extract length-prefixed strings from protobuf-like binary data.

    Walks the byte stream looking for sequences that decode as readable UTF-8.
    Uses a combination of protobuf wire-type-2 (length-delimited) parsing and
    fallback regex extraction.
    """
    strings: list[str] = []

    # Strategy 1: walk protobuf-style length-delimited fields
    i = 0
    while i < len(data) - 1:
        byte = data[i]
        # Check for wire type 2 (length-delimited): low 3 bits == 0b010
        if (byte & 0x07) == 0x02:
            i += 1
            if i >= len(data):
                break
            length = data[i]
            i += 1
            if length > 0 and i + length <= len(data):
                chunk = data[i : i + length]
                try:
                    text = chunk.decode("utf-8")
                    if _is_readable(text) and len(text) >= 3:
                        strings.append(text)
                except UnicodeDecodeError:
                    pass
                i += length
            else:
                # length didn't make sense, skip
                pass
        else:
            i += 1

    # Strategy 2: fallback regex on the raw bytes for any missed strings
    # Look for runs of printable ASCII/UTF-8 at least 5 chars long
    if len(strings) < 2:
        for match in re.finditer(rb"[\x20-\x7e]{5,}", data):
            text = match.group().decode("ascii", errors="ignore").strip()
            if text and text not in strings and _is_readable(text):
                strings.append(text)

    return strings


def _is_readable(text: str) -> bool:
    """Check if a string looks like human-readable ad copy or a URL."""
    if len(text) < 3:
        return False
    # Reject strings that are mostly non-printable or control characters
    printable_count = sum(1 for c in text if c.isprintable())
    return printable_count / len(text) > 0.8


def _looks_like_url(text: str) -> bool:
    """Heuristic: does this string look like a URL or domain?"""
    return bool(
        text.startswith(("http://", "https://", "www."))
        or re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text)
    )
