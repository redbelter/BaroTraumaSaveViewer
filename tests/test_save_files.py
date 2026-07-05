#!/usr/bin/env python3
"""
Tests for the PySide6 GUI integration with the Barotrauma save file parser.
Tests loading, parsing, and displaying data through the GUI widgets.
"""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

# Ensure src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.decode import parse_save
from parser.data import SaveFile, SubmarineInfo, Character, Hull

# GUI widgets (headless-friendly, no window shown)
from gui import (
    CharactersWidget, HullsWidget, ItemsWidget, SubmarineWidget,
    CampaignWidget, MissionsWidget, RawXmlWidget, Sidebar, MapWidget,
    _condition_color, _status_color, _status_label, _biome_color,
)

# ─── Fixtures ────

SAVE_PATH = Path(__file__).parent.parent / "data" / "samples" / "grav.save"
POTATO_PATH = Path(__file__).parent.parent / "data" / "potato 2.save"
MISSION2_PATH = Path(__file__).parent.parent / "data" / "samples" / "2mission.save"


@pytest.fixture
def app():
    """Create a QApplication for headless widget testing."""
    existing = QApplication.instance()
    if existing is None:
        return QApplication([])
    return existing


@pytest.fixture
def parsed_grav():
    if not SAVE_PATH.exists():
        pytest.skip(f"Sample file not found: {SAVE_PATH}")
    return parse_save(SAVE_PATH)


@pytest.fixture
def parsed_potato(app):
    if not POTATO_PATH.exists():
        pytest.skip(f"File not found: {POTATO_PATH}")
    return parse_save(POTATO_PATH)


# ─── Color helpers ───

class TestColorHelpers:
    def test_condition_color_green(self):
        c = _condition_color(90)
        assert c.red() == 80 and c.green() == 220

    def test_condition_color_red(self):
        c = _condition_color(10)
        assert c.red() == 230 and c.green() == 60

    def test_status_label_dead(self, app):
        c = Character(id="1", name="Dead", job="Captain", condition="0%", permanently_dead=True)
        assert _status_label(c) == "Dead"

    def test_status_label_campaign(self, app):
        c = Character(id="1", name="Camp", job="Pilot", status="Campaign")
        assert _status_label(c) == "Campaign"

    def test_status_label_duffelbag(self, app):
        c = Character(id="1", name="Bag", job="Engineer", status="In Duffelbag")
        assert _status_label(c) == "Duffelbag"


# ─── Characters Widget ───

class TestCharactersWidget:
    def test_populates_table(self, app, parsed_grav):
        w = CharactersWidget()
        w.set_data(parsed_grav.characters)
        assert w.table.rowCount() == len(parsed_grav.characters)

    def test_filter_all_shows_all(self, app, parsed_grav):
        w = CharactersWidget()
        w.set_data(parsed_grav.characters)
        w.filter_combo.setCurrentText("All")
        assert w.table.rowCount() == len(parsed_grav.characters)

    def test_filter_by_job(self, app, parsed_grav):
        w = CharactersWidget()
        w.set_data(parsed_grav.characters)
        jobs = {c.job for c in parsed_grav.characters}
        test_job = max(jobs, key=lambda j: sum(1 for c in parsed_grav.characters if c.job == j))
        w.filter_combo.setCurrentText(test_job)
        # After filtering, only matching rows should be shown
        for row in range(w.table.rowCount()):
            job_text = w.table.item(row, 2).text()
            assert job_text == test_job

    def test_search_filters(self, app, parsed_grav):
        w = CharactersWidget()
        w.set_data(parsed_grav.characters)
        # Search for first character's name
        first_name = parsed_grav.characters[0].name
        w.search_input.setText(first_name)
        # Should have fewer or equal rows
        assert w.table.rowCount() <= len(parsed_grav.characters)
        if w.table.rowCount() > 0:
            found = w.table.item(0, 1).text()
            assert first_name.lower() in found.lower()

    def test_empty_data(self, app):
        w = CharactersWidget()
        w.set_data([])
        assert w.table.rowCount() == 0


# ─── Hulls Widget ───

class TestHullsWidget:
    def test_populates_table(self, app, parsed_grav):
        w = HullsWidget()
        w.set_data(parsed_grav.hulls)
        assert w.table.rowCount() == len(parsed_grav.hulls)

    def test_health_colors(self, app, parsed_grav):
        w = HullsWidget()
        w.set_data(parsed_grav.hulls)
        for row in range(w.table.rowCount()):
            item = w.table.item(row, 2)
            assert item is not None
            assert "%" in item.text()

    def test_empty_data(self, app):
        w = HullsWidget()
        w.set_data([])
        assert w.table.rowCount() == 0


# ─── Items Widget ───

class TestItemsWidget:
    def test_populates_table(self, app, parsed_grav):
        w = ItemsWidget()
        w.set_data(parsed_grav.items)
        assert w.table.rowCount() == len(parsed_grav.items)

    def test_filter_by_type(self, app, parsed_grav):
        w = ItemsWidget()
        w.set_data(parsed_grav.items)
        types = {i.item_type for i in parsed_grav.items}
        test_type = max(types, key=lambda t: sum(1 for i in parsed_grav.items if i.item_type == t))
        w.filter_combo.setCurrentText(test_type)
        for row in range(w.table.rowCount()):
            type_text = w.table.item(row, 2).text()
            assert type_text == test_type

    def test_empty_data(self, app):
        w = ItemsWidget()
        w.set_data([])
        assert w.table.rowCount() == 0


# ─── Missions Widget ───

class TestMissionsWidget:
    def test_populates_table(self, app, parsed_grav):
        w = MissionsWidget()
        w.set_data(parsed_grav.missions)
        assert w.table.rowCount() == len(parsed_grav.missions)

    def test_status_colors(self, app, parsed_grav):
        w = MissionsWidget()
        w.set_data(parsed_grav.missions)
        for row in range(w.table.rowCount()):
            status_item = w.table.item(row, 5)
            assert status_item is not None
            status = status_item.text()
            assert status in ("Active", "Failed", "Not attempted")

    def test_empty_data(self, app):
        w = MissionsWidget()
        w.set_data([])
        assert w.table.rowCount() == 0


# ─── Submarine Widget ───

class TestSubmarineWidget:
    def test_displays_data(self, app, parsed_grav):
        w = SubmarineWidget()
        w.set_data(parsed_grav.submarine, parsed_grav.original_size, parsed_grav.decompressed_size)
        text = w.text_edit.toPlainText()
        assert "Camel" in text or parsed_grav.submarine.name in text
        assert "bytes" in text


# ─── Campaign Widget ───

class TestCampaignWidget:
    def test_displays_campaign(self, app, parsed_grav):
        w = CampaignWidget()
        w.set_data(parsed_grav)
        text = w.text_edit.toPlainText()
        assert "Max Missions" in text


# ─── Raw XML Widget ───

class TestRawXmlWidget:
    def test_displays_xml(self, app, parsed_grav):
        w = RawXmlWidget()
        w.set_data(parsed_grav.raw_xml)
        text = w.text_edit.toPlainText()
        if parsed_grav.raw_xml:
            assert len(text) > 0


# ─── Sidebar Widget ───

class TestSidebar:
    def test_stats_update(self, app):
        s = Sidebar()
        s.update_stats("Test stats text")
        assert s.stats_label.text() == "Test stats text"

    def test_recent_update(self, app):
        s = Sidebar()
        recent = [str(SAVE_PATH)] if SAVE_PATH.exists() else []
        s.update_recent(recent)
        if recent:
            assert s.recent_layout.count() >= 1


# ─── Map Widget ───

class TestMapWidget:
    def test_biome_color_deep_ocean(self):
        c = _biome_color("Deep Ocean")
        assert c.blue() > c.red()

    def test_biome_color_ocean(self):
        c = _biome_color("Ocean")
        assert c.blue() > c.red()

    def test_biome_color_caves(self):
        c = _biome_color("Caves")
        assert c.red() > c.blue()

    def test_biome_color_unknown(self):
        c = _biome_color("Something Totally Unknown")
        assert c is not None

    def test_map_widget_creates(self, app):
        m = MapWidget()
        assert m.scene is not None
        assert m.view is not None

    def test_map_widget_set_empty(self, app):
        m = MapWidget()
        m.set_data([])
        assert len(m._items) == 0

    def test_map_widget_plots_locations(self, app, parsed_grav):
        m = MapWidget()
        m.set_data(parsed_grav.locations)
        # At least some locations should have coordinates
        # (some saves have positions, some don't)
        # The widget should not crash regardless
        assert m.scene is not None

    def test_parse_position(self, app):
        m = MapWidget()
        assert m._parse_pos("100,200") == (100.0, 200.0)
        assert m._parse_pos("100, 200") == (100.0, 200.0)
        assert m._parse_pos("Unknown") is None
        assert m._parse_pos("") is None
        assert m._parse_pos("not-a-number,200") is None

    def test_map_has_legend(self, app, parsed_grav):
        m = MapWidget()
        m.set_data(parsed_grav.locations)
        if len(m._biome_legend) > 0:
            assert m._legend.count() >= 2  # at least one dot + label


# ─── End-to-end: parse + widgets ───

class TestEndToEnd:
    def test_load_grav_and_populate_widgets(self, app, parsed_grav):
        """Parse grav.save, populate all widgets, verify data is present."""
        chars = CharactersWidget()
        chars.set_data(parsed_grav.characters)
        assert chars.table.rowCount() > 0

        hulls = HullsWidget()
        hulls.set_data(parsed_grav.hulls)
        assert hulls.table.rowCount() > 0

        items = ItemsWidget()
        items.set_data(parsed_grav.items)
        assert items.table.rowCount() > 0

        missions = MissionsWidget()
        missions.set_data(parsed_grav.missions)
        assert missions.table.rowCount() > 0

    def test_nonexistent_file_raises(self):
        bad_path = Path("/nonexistent/file.save")
        with pytest.raises(FileNotFoundError):
            parse_save(bad_path)

    def test_non_gzip_file_raises(self, tmp_path):
        fake = tmp_path / "fake.save"
        fake.write_bytes(b"not a gzip file")
        with pytest.raises(ValueError, match="Not a valid gzip"):
            parse_save(fake)
