"""Parse data from Barotrauma save files."""

from __future__ import annotations

import io
import gzip
from pathlib import Path


def decompress_gzip_layer(data: bytes) -> bytes | None:
    """Decompress one gzip layer. Returns None if not valid."""
    try:
        buf = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buf) as gz:
            return gz.read()
    except Exception:
        return None


def extract_files(data: bytes) -> list[dict]:
    """Extract files from level-0 data.

    Format per file:
    - 4 bytes: filename length (u32 LE)
    - N*2 bytes: UTF-16LE filename
    - 4 bytes: content length (u32 LE)
    - M bytes: content
    """
    files = []
    i = 0
    while i + 4 <= len(data):
        name_len = int.from_bytes(data[i : i + 4], "little")
        if name_len < 0 or name_len > 10000 or i + name_len * 2 > len(data):
            break
        i += 4
        name = data[i : i + name_len * 2].decode("utf-16-le", errors="replace")
        i += name_len * 2
        if i + 4 > len(data):
            break
        content_len = int.from_bytes(data[i : i + 4], "little")
        if content_len < 0 or content_len > 100_000_000 or i + 4 + content_len > len(data):
            break
        i += 4
        content = data[i : i + content_len]
        i += content_len
        files.append({"name": name, "content": content, "decompressed": None})
    return files


def _try_decompress(f: dict) -> bytes:
    """Decompress a file's content. Returns raw bytes if not gzip."""
    raw = f["content"]
    if len(raw) > 2 and raw[:2] == b"\x1f\x8b":
        result = decompress_gzip_layer(raw)
        if result and len(result) > 0:
            f["decompressed"] = result
            return result
    f["decompressed"] = raw
    return raw


def load_save(path: Path) -> dict:
    """Load and decompress a save file. Returns dict with all files."""
    data = path.read_bytes()
    decompressed_size = len(data)

    level0 = decompress_gzip_layer(data)
    if level0 is None:
        raise ValueError(f"Not a valid gzip file: {path.name}")
    decompressed_size = len(level0)

    files = extract_files(level0)
    for f in files:
        _try_decompress(f)

    return {
        "path": path,
        "original_size": len(data),
        "decompressed_size": decompressed_size,
        "files": files,
    }


def parse_submarine(xml_str: str) -> dict:
    """Parse submarine info from XML. Returns dict."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    return {
        "name": root.get("name", "Unknown"),
        "sub_type": root.get("type", "Unknown"),
        "class_": root.get("class", "Unknown"),
        "tier": root.get("tier", "Unknown"),
        "game_version": root.get("gameversion", "Unknown"),
        "dimensions": root.get("dimensions", "Unknown"),
        "cargo_capacity": root.get("cargocapacity", "Unknown"),
        "price": root.get("price", "Unknown"),
        "tags": root.get("Tags", "Unknown"),
    }
