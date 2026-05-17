#!/usr/bin/env python3
"""CLI entry point for reverse-baro."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as python -m reverse_baro.cli
try:
    from parser.data import SaveFile
    from parser.decode import parse_save
except ImportError:
    # Running directly
    from data import SaveFile
    from decode import parse_save

# Alias for backwards compatibility
load_and_decompress = parse_save


def cmd_info(args: argparse.Namespace) -> None:
    """Show summary info for one or more save files."""
    paths = _resolve_paths(args.files)
    for path in paths:
        print(f"\n{'='*60}")
        print(f"  {path.name}")
        print(f"{'='*60}")
        print(f"  Size:       {path.stat().st_size:>10,} bytes")
        try:
            sf = load_and_decompress(path)
            print(f"  Decompressed: {sf.decompressed_size:>10,} bytes")
            print(f"  Submarine:    {sf.submarine.name:<40s} (tier {sf.submarine.tier})")
            print(f"  Type/Class:   {sf.submarine.sub_type}/{sf.submarine.class_}")
            print(f"  Characters:   {len(sf.characters)}")
            print(f"  Hulls:        {len(sf.hulls)}")
            print(f"  Items:        {len(sf.items)}")
            print(f"  Locations:    {len(sf.locations)}")
            print(f"  Missions:     {len(sf.missions)}")
            if sf.campaign_settings:
                cs = sf.campaign_settings
                print(f"  Max Missions: {cs.max_mission_count}")
        except Exception as e:
            print(f"  ERROR: {e}")


def cmd_chars(args: argparse.Namespace) -> None:
    """List characters from a save file."""
    paths = _resolve_paths(args.files)
    for path in paths:
        print(f"\n  {path.name}")
        print(f"  {'ID':<10} {'Name':<30} {'Job':<20} {'Condition':<12} {'Status'}")
        print(f"  {'-'*85}")
        try:
            sf = load_and_decompress(path)
            for c in sf.characters:
                print(f"  {c.id:<10} {c.name:<30} {c.job:<20} {c.condition:<12} {c.status}")
        except Exception as e:
            print(f"  ERROR: {e}")


def cmd_missions(args: argparse.Namespace) -> None:
    """List missions from save files."""
    paths = _resolve_paths(args.files)
    for path in paths:
        print(f"\n  {path.name}")
        sf = load_and_decompress(path)
        if not sf.missions:
            print("  No missions found.")
            continue
        for m in sf.missions:
            mark = "✓" if m.selected else " "
            print(f"  [{mark}] {m.prefab_id:<35s} -> {m.location:<20s} (tried {m.times_attempted}x)")


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare two save files."""
    p1, p2 = _resolve_paths(args.files[:1])[0], _resolve_paths(args.files[1:2])[0]

    sf1 = load_and_decompress(p1)
    sf2 = load_and_decompress(p2)

    print(f"\n  Comparison: {p1.name} vs {p2.name}")
    print(f"  {'='*50}")
    print(f"\n  Submarines:")
    print(f"    {p1.name}: {sf1.submarine.name} (tier {sf1.submarine.tier})")
    print(f"    {p2.name}: {sf2.submarine.name} (tier {sf2.submarine.tier})")
    print(f"\n  Stats:")
    print(f"    Characters: {len(sf1.characters)} -> {len(sf2.characters)}")
    print(f"    Hulls:      {len(sf1.hulls)} -> {len(sf2.hulls)}")
    print(f"    Items:      {len(sf1.items)} -> {len(sf2.items)}")
    print(f"    Missions:   {len(sf1.missions)} -> {len(sf2.missions)}")

    # Mission comparison
    set1 = {(m.prefab_id, m.location) for m in sf1.missions}
    set2 = {(m.prefab_id, m.location) for m in sf2.missions}
    added = set2 - set1
    removed = set1 - set2

    if added:
        print(f"\n  Added to {p2.name}:")
        for prefab, loc in sorted(added):
            print(f"    + {prefab:<40s} -> {loc}")
    if removed:
        print(f"\n  Removed from {p2.name}:")
        for prefab, loc in sorted(removed):
            print(f"    - {prefab:<40s} -> {loc}")


def cmd_json(args: argparse.Namespace) -> None:
    """Export a save file to JSON."""
    paths = _resolve_paths(args.files)
    for path in paths:
        sf = load_and_decompress(path)
        data = _savefile_to_dict(sf)
        if args.output:
            Path(args.output).write_text(json.dumps(data, indent=2, default=str))
            print(f"  Written to {args.output}")
        else:
            print(json.dumps(data, indent=2, default=str))


def _savefile_to_dict(sf: SaveFile) -> dict:
    return {
        "filename": str(sf.path),
        "original_size": sf.original_size,
        "decompressed_size": sf.decompressed_size,
        "submarine": vars(sf.submarine),
        "characters": [vars(c) for c in sf.characters],
        "hulls": [vars(h) for h in sf.hulls],
        "structures": [vars(s) for s in sf.structures],
        "gaps": [vars(g) for g in sf.gaps],
        "items": [vars(i) for i in sf.items],
        "locations": [vars(l) for l in sf.locations],
        "missions": [vars(m) for m in sf.missions],
        "campaign_settings": vars(sf.campaign_settings) if sf.campaign_settings else None,
    }


def _resolve_paths(files: list[str]) -> list[Path]:
    paths = []
    for f in files:
        p = Path(f)
        if not p.exists():
            # Try common save locations
            for loc in [
                Path.home() / "AppData" / "LocalLow" / "Eyefish" / "Barotrauma" / "saves",
                Path.cwd() / "saves",
            ]:
                candidate = loc / p.name
                if candidate.exists():
                    p = candidate
                    break
        if not p.exists():
            print(f"  ERROR: File not found: {f}", file=sys.stderr)
            sys.exit(1)
        paths.append(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reverse-baro",
        description="Parse and analyze Barotrauma save files",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    info_p = sub.add_parser("info", help="Show summary info for save files")
    info_p.add_argument("files", nargs="+", help="Save file(s) to inspect")

    # chars
    chars_p = sub.add_parser("chars", help="List characters")
    chars_p.add_argument("files", nargs="+")

    # missions
    missions_p = sub.add_parser("missions", help="List missions")
    missions_p.add_argument("files", nargs="+")

    # compare
    compare_p = sub.add_parser("compare", help="Compare two save files")
    compare_p.add_argument("files", nargs=2)

    # json
    json_p = sub.add_parser("json", help="Export to JSON")
    json_p.add_argument("files", nargs="+")
    json_p.add_argument("-o", "--output", help="Output file (default: stdout)")

    args = parser.parse_args()
    {"info": cmd_info, "chars": cmd_chars, "missions": cmd_missions,
     "compare": cmd_compare, "json": cmd_json}[args.command](args)


if __name__ == "__main__":
    main()
