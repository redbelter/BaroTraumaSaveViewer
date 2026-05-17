"""Extract files from Barotrauma save file structure.

Barotrauma .save files use a custom format:
  [u32 len of filename][filename bytes][u32 len of content][content bytes]...
"""

from __future__ import annotations

import gzip
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .data import SaveFile
from .parse import (
    parse_campaign,
    parse_characters_from_xml,
    parse_gaps_from_xml,
    parse_hulls_from_xml,
    parse_items_from_xml,
    parse_structures_from_xml,
    parse_submarine,
)


def decompress_gzip_layer(data: bytes) -> bytes | None:
    """Decompress one gzip layer. Returns None if not valid."""
    try:
        buf = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buf) as gz:
            return gz.read()
    except (gzip.BadGzipFile, EOFError, OSError):
        return None


def extract_raw_files(data: bytes) -> list[dict]:
    """Extract raw files from level-0 data.

    Format per file:
    - 4 bytes: filename length (u32 LE)
    - N*2 bytes: UTF-16LE filename
    - 4 bytes: content length (u32 LE)
    - M bytes: content
    """
    files: list[dict] = []
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


def _try_decompress(file_dict: dict) -> bytes:
    """Decompress file content. If not gzip, return raw bytes."""
    raw = file_dict["content"]
    # Check for gzip magic bytes first
    if len(raw) > 2 and raw[:2] == b"\x1f\x8b":
        result = decompress_gzip_layer(raw)
        if result and len(result) > 0:
            file_dict["decompressed"] = result
            return result
    # Not gzip or failed — return original bytes (e.g., raw XML like gamesession.xml)
    file_dict["decompressed"] = raw
    return raw


def parse_save(path: Path) -> SaveFile:
    """Full pipeline: load, decompress, parse all XML into dataclasses."""
    data = path.read_bytes()
    sf = SaveFile(path=path, original_size=len(data))

    # Level 0: outer gzip
    level0 = decompress_gzip_layer(data)
    if level0 is None:
        raise ValueError(f"Not a valid gzip: {path.name}")
    sf.decompressed_size = len(level0)

    raw_files = extract_raw_files(level0)
    if not raw_files:
        raise ValueError(f"No files found in {path.name}")

    # Decompress each file's content
    for f in raw_files:
        _try_decompress(f)

    # Categorize files
    gamesession_xml = None
    submarine_files: list[dict] = []
    char_data_file: str | None = None

    for f in raw_files:
        if f["decompressed"] is None:
            continue
        name_lower = f["name"].lower()
        if "gamesession" in name_lower:
            gamesession_xml = f
        elif name_lower.endswith(".sub"):
            submarine_files.append(f)
        elif "characterdata" in name_lower:
            char_data_file = f["name"]

    # Parse gamesession.xml for campaign data (characters, missions, locations)
    if gamesession_xml is not None:
        xml_str = gamesession_xml["decompressed"].decode("utf-8", errors="ignore")
        raw_xml = xml_str
        parse_campaign(xml_str, sf)
        sf.raw_xml = raw_xml

    # Parse all .sub files for hulls, structures, items, gaps
    for sub_file in submarine_files:
        if sub_file["decompressed"] is None:
            continue
        xml_str = sub_file["decompressed"].decode("utf-8", errors="ignore")
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_str)
            if root.tag != "Submarine":
                continue

            # Parse submarine info
            if sf.submarine.name == "Unknown":
                sf.submarine = parse_submarine(xml_str)

            # Parse hulls (may be bare <Hull ID="..."/> with no extra attributes)
            for h in parse_hulls_from_xml(xml_str):
                if not any(h.id == x.id for x in sf.hulls):
                    sf.hulls.append(h)

            # Parse structures
            for s in parse_structures_from_xml(xml_str):
                if not any(s.id == x.id for x in sf.structures):
                    sf.structures.append(s)

            # Parse gaps
            for g in parse_gaps_from_xml(xml_str):
                if not any(g.id == x.id for x in sf.gaps):
                    sf.gaps.append(g)

            # Parse items (skip if noitems="true")
            if root.get("noitems", "false").lower() != "true":
                for i in parse_items_from_xml(xml_str):
                    if not any(i.id == x.id for x in sf.items):
                        sf.items.append(i)
        except Exception as e:
            print(f"Warning: Failed to parse {sub_file['name']}: {e}", file=sys.stderr)

    # If no characters found, look for them in gamesession
    if not sf.characters and gamesession_xml:
        sf.characters = parse_characters_from_xml(gamesession_xml["decompressed"].decode("utf-8", errors="ignore"), "Campaign")

    sf.raw_xml = gamesession_xml["decompressed"].decode("utf-8", errors="ignore") if gamesession_xml else ""
    return sf
