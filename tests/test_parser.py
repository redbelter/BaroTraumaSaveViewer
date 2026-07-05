"""Comprehensive tests for reverse-baro parser.

Tests all parsing functions, dataclasses, and save file decompression
against the actual grav.save sample file to ensure data completeness.
"""

import gzip
import io
import json
import sys
from dataclasses import asdict
from pathlib import Path
import xml.etree.ElementTree as ET

# Ensure parser is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from parser.data import (
    SaveFile,
    SubmarineInfo,
    Character,
    Hull,
    Structure,
    Gap,
    Item,
    Location,
    Mission,
    CampaignSettings,
    item_type_from_identifier,
)
from parser.decode import parse_save, extract_raw_files, _try_decompress
from parser.parse import (
    parse_submarine,
    parse_campaign,
    parse_characters_from_xml,
    parse_hulls_from_xml,
    parse_structures_from_xml,
    parse_gaps_from_xml,
    parse_items_from_xml,
)


# ── Fixtures ──

SAVE_PATH = Path(__file__).parent.parent / "data" / "samples" / "grav.save"


def get_level0_data() -> bytes:
    """Read and decompress grav.save to get raw level-0 data."""
    assert SAVE_PATH.exists(), f"Sample file not found: {SAVE_PATH}"
    data = SAVE_PATH.read_bytes()
    buf = io.BytesIO(data)
    with gzip.GzipFile(fileobj=buf) as gz:
        return gz.read()


@pytest.fixture
def level0_data() -> bytes:
    return get_level0_data()


@pytest.fixture
def raw_files(level0_data: bytes) -> list[dict]:
    return extract_raw_files(level0_data)


@pytest.fixture
def parsed_save() -> SaveFile:
    return parse_save(SAVE_PATH)


def get_gamesession_xml() -> str:
    """Get the gamesession.xml as a string."""
    data = get_level0_data()
    files = extract_raw_files(data)
    for f in files:
        if "gamesession" in f["name"].lower():
            return _try_decompress(f).decode("utf-8", errors="ignore")
    raise ValueError("No gamesession found")


# ══════════════════════════════════════════════════════════════
# ITEM TYPE DETECTION (fix bug #1)
# ══════════════════════════════════════════════════════════════

class TestItemTypeFromIdentifier:
    """Test that item types are correctly derived from identifiers."""

    def test_underscored_identifier(self):
        assert item_type_from_identifier("gun_shotgun") == "shotgun"

    def test_underscored_multi_part(self):
        assert item_type_from_identifier("duffelbag_container") == "container"

    def test_underscored_food(self):
        assert item_type_from_identifier("food_meat") == "meat"

    def test_single_word_no_underscore(self):
        """Bug fix: single-word identifiers should return themselves, not 'custom'."""
        assert item_type_from_identifier("idcard") == "idcard"
        assert item_type_from_identifier("weldingtool") == "weldingtool"
        assert item_type_from_identifier("oxygentank") == "oxygentank"
        assert item_type_from_identifier("headset") == "headset"

    def test_uppercase(self):
        assert item_type_from_identifier("gun_SHOTGUN") == "shotgun"

    def test_empty_string(self):
        assert item_type_from_identifier("") == ""


# ══════════════════════════════════════════════════════════════
# SAVE FILE DECOMPRESSION
# ══════════════════════════════════════════════════════════════

class TestDecompression:
    """Test save file decompression and file extraction."""

    def test_outer_gzip_decompresses(self):
        data = SAVE_PATH.read_bytes()
        buf = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buf) as gz:
            level0 = gz.read()
        # Level 0 decompresses to something much larger
        assert len(level0) > len(data)

    def test_extract_files(self, level0_data: bytes):
        files = extract_raw_files(level0_data)
        assert len(files) > 0
        names = [f["name"] for f in files]
        assert any("gamesession" in n for n in names)
        assert any(n.endswith(".sub") for n in names)

    def test_gamesession_is_raw_text(self, raw_files: list[dict]):
        gs = [f for f in raw_files if "gamesession" in f["name"].lower()]
        assert len(gs) == 1
        # gamesession.xml is raw text, not gzip — _try_decompress returns it as-is
        decomp = _try_decompress(gs[0])
        assert decomp is not None
        # It should start with XML declaration or BOM
        text = decomp.decode("utf-8", errors="ignore")
        assert text.startswith("<?xml") or text.startswith("\ufeff")

    def test_sub_files_are_gzip(self, raw_files: list[dict]):
        subs = [f for f in raw_files if f["name"].endswith(".sub")]
        assert len(subs) >= 1
        for sub in subs:
            # .sub files are gzip-compressed
            assert sub["content"][:2] == b"\x1f\x8b"
            decomp = _try_decompress(sub)
            assert decomp is not None
            assert len(decomp) > 0
            # Decompressed .sub files contain XML
            text = decomp.decode("utf-8", errors="ignore")
            assert "<Submarine" in text or "<Hull" in text

    def test_load_and_decompress(self):
        sf = parse_save(SAVE_PATH)
        assert sf.path == SAVE_PATH
        assert sf.original_size > 0
        assert sf.decompressed_size > sf.original_size
        # Should have parsed hulls at minimum
        assert len(sf.hulls) > 0


# ══════════════════════════════════════════════════════════════
# PARSER DATA
# ══════════════════════════════════════════════════════════════

class TestSaveFileData:
    """Test that all data is fully parsed from grav.save."""

    def test_submarine_parsed(self, parsed_save: SaveFile):
        """Submarine should have name/type/class/tier."""
        assert parsed_save.submarine.name != "Unknown", "Submarine name is Unknown"
        assert parsed_save.submarine.sub_type != "Unknown"
        assert parsed_save.submarine.class_ != "Unknown"
        assert parsed_save.submarine.tier != "Unknown"
        assert parsed_save.submarine.dimensions != "Unknown"
        assert parsed_save.submarine.cargo_capacity != "Unknown"
        assert parsed_save.submarine.price != "Unknown"

    def test_hulls_parsed_from_sub(self, parsed_save: SaveFile):
        """Hulls from .sub files must be parsed (bare <Hull ID="x"/>)."""
        assert len(parsed_save.hulls) > 0, "No hulls parsed!"
        for h in parsed_save.hulls:
            assert h.id != "Unknown"
            assert h.health_pct == 100.0  # Template hulls have no healthdata

    def test_structures_parsed_from_sub(self, parsed_save: SaveFile):
        """Structures from .sub files use 'name' attribute, not 'rect'."""
        assert len(parsed_save.structures) > 0, "No structures parsed!"
        for s in parsed_save.structures:
            assert s.id != "Unknown"

    def test_gaps_parsed_from_sub(self, parsed_save: SaveFile):
        assert len(parsed_save.gaps) > 0, "No gaps parsed!"
        for g in parsed_save.gaps:
            assert g.id != "Unknown"

    def test_items_parsed_from_sub(self, parsed_save: SaveFile):
        """Item types must be correct for single-word identifiers."""
        assert len(parsed_save.items) > 0, "No items parsed!"
        for item in parsed_save.items:
            assert item.identifier != "unknown"

    def test_items_have_correct_types(self, parsed_save: SaveFile):
        """weldingtool -> weldingtool, not custom."""
        weld_items = [i for i in parsed_save.items if "weldingtool" in i.identifier.lower()]
        for w in weld_items:
            assert w.item_type == "weldingtool", f"Expected 'weldingtool', got '{w.item_type}'"

    def test_idcard_item_type(self, parsed_save: SaveFile):
        """idcard -> idcard, not custom."""
        idcard_items = [i for i in parsed_save.items if i.identifier == "idcard"]
        for ic in idcard_items:
            assert ic.item_type == "idcard"

    def test_items_have_condition(self, parsed_save: SaveFile):
        """Items should have condition percentages."""
        for item in parsed_save.items:
            assert 0.0 <= item.condition_pct <= 100.0

    def test_characters_parsed(self, parsed_save: SaveFile):
        """Characters should be parsed from gamesession.xml."""
        assert len(parsed_save.characters) > 0, "No characters parsed!"
        for c in parsed_save.characters:
            assert c.name != "Unknown"
            assert c.id != ""

    def test_characters_have_health(self, parsed_save: SaveFile):
        """Characters should have health percentage in condition field."""
        for c in parsed_save.characters:
            assert c.condition != "Unknown"
            assert c.condition.endswith("%")

    def test_missions_parsed(self, parsed_save: SaveFile):
        """Missions should be mapped to locations via Metadata."""
        assert len(parsed_save.missions) > 0, "No missions parsed!"
        for m in parsed_save.missions:
            assert m.prefab_id != "Unknown"
            # Location can be empty if the destinationindex wasn't found
            if m.location:
                assert m.location != "Unknown"

    def test_missions_have_selected_flag(self, parsed_save: SaveFile):
        """Some missions should have selected=True."""
        selected = [m for m in parsed_save.missions if m.selected]
        assert len(selected) > 0, "No missions have selected=True!"

    def test_missions_have_location_names(self, parsed_save: SaveFile):
        """Missions should map to actual location names."""
        selected = [m for m in parsed_save.missions if m.selected]
        for m in selected:
            if m.location:
                assert m.location != "Unknown"

    def test_locations_parsed(self, parsed_save: SaveFile):
        assert len(parsed_save.locations) > 0, "No locations parsed!"
        for loc in parsed_save.locations:
            if loc.name != "Unknown":
                assert loc.location_type != "Unknown", f"Location {loc.name} has Unknown type"

    def test_campaign_settings_parsed(self, parsed_save: SaveFile):
        assert parsed_save.campaign_settings is not None
        cs = parsed_save.campaign_settings
        assert cs.max_mission_count is not None
        assert cs.max_mission_count > 0

    def test_all_dataclasses_serializable(self, parsed_save: SaveFile):
        """Ensure all parsed dataclasses can be serialized."""
        asdict(parsed_save)
        for c in parsed_save.characters:
            asdict(c)
        for h in parsed_save.hulls:
            asdict(h)
        for s in parsed_save.structures:
            asdict(s)
        for g in parsed_save.gaps:
            asdict(g)
        for i in parsed_save.items:
            asdict(i)
        for loc in parsed_save.locations:
            asdict(loc)
        for m in parsed_save.missions:
            asdict(m)


# ══════════════════════════════════════════════════════════════
# SUBMARINE XML PARSING
# ══════════════════════════════════════════════════════════════

class TestSubmarineParsing:
    """Test parsing .sub files directly."""

    def test_parse_submarine_data(self):
        """Parse Camel.sub and verify attributes."""
        data = get_level0_data()
        files = extract_raw_files(data)
        camel = [f for f in files if "Camel" in f["name"]][0]
        decomp = _try_decompress(camel)
        assert decomp is not None

        sub = parse_submarine(decomp.decode("utf-8", errors="ignore"))
        assert sub.name == "Camel"
        assert sub.sub_type == "Player"
        assert sub.class_ == "Transport"
        assert sub.tier == "1"
        assert sub.game_version != "Unknown"
        assert sub.dimensions != "Unknown"

    def test_bare_hull_parses_cleanly(self):
        """Bare <Hull ID="152" /> should not crash and should default to 100% health."""
        xml = '<Submarine><Hull ID="152" /></Submarine>'
        hulls = parse_hulls_from_xml(xml)
        assert len(hulls) == 1
        assert hulls[0].id == "152"
        assert hulls[0].name == "Hull-152"
        assert hulls[0].health_pct == 100.0
        assert hulls[0].integrity == 100.0
        assert hulls[0].damage == 0.0


# ══════════════════════════════════════════════════════════════
# CAMPAIGN SESSION PARSING
# ══════════════════════════════════════════════════════════════

class TestCampaignParsing:
    """Test parsing gamesession.xml campaign data."""

    def test_campaign_settings(self):
        gs_xml = get_gamesession_xml()
        sf = SaveFile(path=SAVE_PATH)
        parse_campaign(gs_xml, sf)
        assert sf.campaign_settings is not None
        assert sf.campaign_settings.max_mission_count == 10

    def test_missions_via_metadata(self):
        """Missions should be extracted from Metadata Data entries."""
        gs_xml = get_gamesession_xml()
        sf = SaveFile(path=SAVE_PATH)
        parse_campaign(gs_xml, sf)
        
        assert len(sf.missions) > 0
        selected = [m for m in sf.missions if m.selected]
        assert len(selected) > 0
        for m in selected:
            assert m.location != "Unknown"

    def test_mission_destinations_mapped(self):
        """Missions should map to actual location names."""
        gs_xml = get_gamesession_xml()
        sf = SaveFile(path=SAVE_PATH)
        parse_campaign(gs_xml, sf)
        
        assert len(sf.missions) > 0
        for m in sf.missions:
            if m.location:
                assert m.location != "Unknown"


# ══════════════════════════════════════════════════════════════
# XML PARSING UNIT TESTS
# ══════════════════════════════════════════════════════════════

class TestXMLParsing:
    """Test individual XML parsing functions."""

    def test_parse_items(self):
        xml = '<Submarine><Item ID="1" identifier="gun_shotgun" conditionpercentage="80.5" /></Submarine>'
        items = parse_items_from_xml(xml)
        assert len(items) == 1
        assert items[0].identifier == "gun_shotgun"
        assert items[0].item_type == "shotgun"
        assert items[0].condition_pct == 80.5

    def test_parse_items_single_word(self):
        xml = '<Submarine><Item ID="1" identifier="idcard" conditionpercentage="100" /></Submarine>'
        items = parse_items_from_xml(xml)
        assert len(items) == 1
        assert items[0].identifier == "idcard"
        assert items[0].item_type == "idcard"

    def test_parse_structures(self):
        xml = '<Submarine><Structure ID="1" name="Test Wall" type="Wall" /></Submarine>'
        structs = parse_structures_from_xml(xml)
        assert len(structs) == 1
        assert structs[0].name == "Test Wall"

    def test_parse_gaps(self):
        xml = '<Submarine><Gap ID="1" /></Submarine>'
        gaps = parse_gaps_from_xml(xml)
        assert len(gaps) == 1
        assert gaps[0].id == "1"

    def test_parse_characters(self):
        xml = '''<Characters>
            <Character id="1" name="Test Captain" job="Captain">
                <health>
                    <LimbHealth i="0" value="100"/>
                    <LimbHealth i="1" value="90"/>
                    <LimbHealth i="2" value="80"/>
                </health>
            </Character>
        </Characters>'''
        chars = parse_characters_from_xml(xml, "Campaign")
        assert len(chars) == 1
        assert chars[0].name == "Test Captain"
        assert chars[0].job == "Captain"
        # Average of 100, 90, 80 = 90
        assert chars[0].condition == "90.00%"


# ══════════════════════════════════════════════════════════════
# END-TO-END VALIDATION
# ══════════════════════════════════════════════════════════════

class TestEndToEnd:
    """Full end-to-end test: parse grav.save and verify data completeness."""

    def test_complete_data_counts(self, parsed_save: SaveFile):
        """Verify we get expected data counts from grav.save."""
        assert parsed_save.submarine.name == "Camel"  # Actual submarine in grav.save
        assert parsed_save.submarine.tier == "1"
        assert len(parsed_save.hulls) > 0, f"Expected hulls, got {len(parsed_save.hulls)}"
        assert len(parsed_save.structures) > 0, f"Expected structures, got {len(parsed_save.structures)}"
        assert len(parsed_save.gaps) > 0, f"Expected gaps, got {len(parsed_save.gaps)}"
        assert len(parsed_save.items) > 0, f"Expected items, got {len(parsed_save.items)}"
        assert len(parsed_save.characters) > 0, f"Expected characters, got {len(parsed_save.characters)}"
        assert len(parsed_save.missions) > 0, f"Expected missions, got {len(parsed_save.missions)}"
        assert len(parsed_save.locations) > 0, f"Expected locations, got {len(parsed_save.locations)}"
        assert parsed_save.campaign_settings is not None

    def test_character_health_details(self, parsed_save: SaveFile):
        """Verify character health comes from <health> subtree."""
        for c in parsed_save.characters:
            assert c.condition.endswith("%"), f"Character {c.name} condition '{c.condition}' doesn't end with %"
            pct = float(c.condition.rstrip("%"))
            assert 0 <= pct <= 100

    def test_mission_selection(self, parsed_save: SaveFile):
        """Verify selected missions have location names mapped."""
        selected = [m for m in parsed_save.missions if m.selected]
        assert len(selected) > 0, "No missions have selected=True"
        for m in selected:
            if m.location:
                assert m.location != "Unknown"

    def test_json_export_roundtrip(self, parsed_save: SaveFile):
        """Export to JSON and parse back."""
        data = {
            "filename": str(parsed_save.path),
            "original_size": parsed_save.original_size,
            "submarine": vars(parsed_save.submarine),
            "characters": [vars(c) for c in parsed_save.characters],
            "hulls": [vars(h) for h in parsed_save.hulls],
            "structures": [vars(s) for s in parsed_save.structures],
            "gaps": [vars(g) for g in parsed_save.gaps],
            "items": [vars(i) for i in parsed_save.items],
            "locations": [vars(l) for l in parsed_save.locations],
            "missions": [vars(m) for m in parsed_save.missions],
            "campaign_settings": vars(parsed_save.campaign_settings) if parsed_save.campaign_settings else None,
        }
        json_str = json.dumps(data, indent=2, default=str)
        parsed_back = json.loads(json_str)
        assert parsed_back["submarine"]["name"] == "Camel"
        assert len(parsed_back["characters"]) > 0
        assert len(parsed_back["missions"]) > 0

    def test_no_broken_ids(self, parsed_save: SaveFile):
        """Ensure no entity has an 'Unknown' or empty ID."""
        for h in parsed_save.hulls:
            assert h.id and h.id != "Unknown"
        for s in parsed_save.structures:
            assert s.id and s.id != "Unknown"
        for g in parsed_save.gaps:
            assert g.id and g.id != "Unknown"
        for i in parsed_save.items:
            assert i.id and i.id != "Unknown"
            assert i.identifier and i.identifier != "unknown"
        for c in parsed_save.characters:
            assert c.name and c.name != "Unknown"
            assert c.id

    def test_no_custom_item_types(self, parsed_save: SaveFile):
        """All items should have a valid type, not 'custom'."""
        custom_items = [i for i in parsed_save.items if i.item_type == "custom"]
        assert len(custom_items) == 0, f"Found {len(custom_items)} items with type='custom': {[i.identifier for i in custom_items[:5]]}"


# ══════════════════════════════════════════════════════════════
# TEST DATA INTEGRITY
# ══════════════════════════════════════════════════════════════

class TestDataIntegrity:
    """Test that the sample data is intact and valid."""

    def test_save_file_exists(self):
        assert SAVE_PATH.exists(), f"Sample save file not found: {SAVE_PATH}"

    def test_save_file_size_reasonable(self):
        size = SAVE_PATH.stat().st_size
        assert size > 1000, f"Save file too small: {size} bytes"

    def test_save_file_valid_gzip(self):
        data = SAVE_PATH.read_bytes()
        buf = io.BytesIO(data)
        with gzip.GzipFile(fileobj=buf) as gz:
            level0 = gz.read()
        assert len(level0) > len(data)

    def test_save_file_has_all_file_types(self, raw_files: list[dict]):
        names = [f["name"].lower() for f in raw_files]
        assert any("gamesession" in n for n in names)
        assert any(n.endswith(".sub") for n in names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
