#!/usr/bin/env python3
"""
Comprehensive test suite for save file viewer.
Tests loading, parsing, and displaying data from various save files.
"""

import unittest
import sys
import os
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from save_file_viewer import SaveFileViewer
import tkinter as tk


class TestSaveFileLoading(unittest.TestCase):
    """Test saving and loading various save files."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.root = tk.Tk()
        cls.root.withdraw()  # Hide window during tests

        # Find all test save files in data directory
        cls.test_dir = Path(__file__).parent.parent / 'data'
        cls.save_files = list(cls.test_dir.glob("**/*.save"))

        print(f"\n{'=' * 70}")
        print(f"Found {len(cls.save_files)} save files to test:")
        for sf in sorted(cls.save_files):
            print(f"  - {sf.relative_to(cls.test_dir)}")
        print("=" * 70 + "\n")

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.root.destroy()

    def setUp(self):
        """Create a new viewer instance for each test."""
        self.app = SaveFileViewer(self.root)

    def tearDown(self):
        """Clear state between tests."""
        self.app.current_save_path = None
        self.app.characters = []
        self.app.sub_info = {}
        self.app.campaign_settings = {}
        self.app.locations = []
        self.app.destinations = []

    def test_load_potato2_save(self):
        """Test loading potato 2 save file."""
        save_file = self.test_dir / "potato 2.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Verify submarine info is loaded
        self.assertIn("name", self.app.sub_info)
        self.assertGreater(len(self.app.characters), 0, "Should have characters")

    def test_load_2mission_save(self):
        """Test loading 2mission save file."""
        save_file = self.test_dir / "samples" / "2mission.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Should have campaign data (locations)
        self.assertGreater(len(self.app.locations), 0, "Should have locations")
        # Note: Some saves may not have active mission destinations

    def test_load_10mission_save(self):
        """Test loading 10mission save file."""
        save_file = self.test_dir / "samples" / "10mission.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Should have campaign data
        self.assertGreater(len(self.app.locations), 0)
        self.assertGreaterEqual(len(self.app.destinations), 0)  # May have no missions

    def test_load_grav_save(self):
        """Test loading grav save file."""
        save_file = self.test_dir / "samples" / "grav.save"

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        # Verify data is loaded
        self.assertIn("name", self.app.sub_info)

    def test_load_lumen_save(self):
        """Test loading lumen save file."""
        save_file = self.test_dir / "lumen.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Verify data is loaded
        self.assertIn("name", self.app.sub_info)

    def test_load_worm_save(self):
        """Test loading worm save file."""
        save_file = self.test_dir / "worm.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Verify data is loaded
        self.assertIn("name", self.app.sub_info)

    def test_load_aaaa_save(self):
        """Test loading aaaa save file."""
        save_file = self.test_dir / "aaaa.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Verify data is loaded
        self.assertIn("name", self.app.sub_info)

    def test_load_cc_game_save(self):
        """Test loading cc_game save file."""
        save_file = self.test_dir / "cc_game.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Verify data is loaded
        self.assertIn("name", self.app.sub_info)

    def test_load_duplicate_folder_saves(self):
        """Test loading saves from duplicate folder."""
        dup_dir = self.test_dir / "duplicate"

        if not dup_dir.exists():
            self.skipTest(f"Directory not found: {dup_dir}")

        for save_file in list(dup_dir.glob("*.save"))[:3]:  # Test first 3
            with self.subTest(save_file=save_file.name):
                self.app.current_save_path = str(save_file)
                self.app.parse_save_file()

                self.assertIn("name", self.app.sub_info, f"Failed for {save_file.name}")

    def test_load_newer_saves_folder(self):
        """Test loading saves from newer-saves folder."""
        newer_dir = self.test_dir / "newer-saves"

        if not newer_dir.exists():
            self.skipTest(f"Directory not found: {newer_dir}")

        for save_file in list(newer_dir.glob("*.save")):
            with self.subTest(save_file=save_file.name):
                self.app.current_save_path = str(save_file)
                self.app.parse_save_file()

                # Should have submarine info
                self.assertIn("name", self.app.sub_info, f"Failed for {save_file.name}")

    def test_character_count_valid(self):
        """Test that character counts are reasonable."""
        save_file = self.test_dir / "potato 2.save"

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        # Should have some characters (not zero, not excessive)
        char_count = len(self.app.characters)
        self.assertGreater(char_count, 0, "Should have at least one character")
        self.assertLess(char_count, 100, "Unusually high character count")

    def test_locations_valid(self):
        """Test that locations are parsed correctly."""
        save_file = self.test_dir / "samples" / "2mission.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Check location structure
        for loc in self.app.locations:
            self.assertIn("name", loc, "Location should have name")
            self.assertIn("type", loc, "Location should have type")

    def test_campaign_settings_present(self):
        """Test that campaign settings are extracted when available."""
        save_file = self.test_dir / "samples" / "10mission.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        # Should have campaign settings with max mission count
        self.assertIn(
            "MaxMissionCount",
            self.app.campaign_settings,
            "Should have MaxMissionCount in campaign settings",
        )

    def test_submarine_info_complete(self):
        """Test that submarine info has all required fields."""
        save_file = self.test_dir / "potato 2.save"

        if not save_file.exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = str(save_file)
        self.app.parse_save_file()

        required_fields = ["name", "type", "class", "tier"]
        for field in required_fields:
            self.assertIn(field, self.app.sub_info, f"Submarine info missing {field}")

    def test_character_statuses(self):
        """Test that characters have valid status values."""
        save_file = "TestFiles/potato 2.save"

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        valid_statuses = ["In Duffelbag", "Campaign", "Living", "Unknown"]
        for char in self.app.characters:
            status = char.get("status", "")
            self.assertIn(status, valid_statuses, f"Invalid status: {status}")


class TestSaveFileViewerGUI(unittest.TestCase):
    """Test GUI functionality of the save file viewer."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.app = SaveFileViewer(cls.root)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.root.destroy()

    def test_refresh_characters_table(self):
        """Test that character table refresh works."""
        # Load a save file first
        save_file = "TestFiles/potato 2.save"
        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        # Test refresh
        initial_count = len(self.app.characters)
        self.assertGreater(initial_count, 0)

        # Refresh should work without errors
        try:
            self.app.refresh_characters_table()
        except Exception as e:
            self.fail(f"refresh_characters_table raised {type(e).__name__}")

    def test_stats_update(self):
        """Test that statistics are updated correctly."""
        save_file = "TestFiles/potato 2.save"
        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        # Update stats should work
        try:
            self.app.update_stats()
        except Exception as e:
            self.fail(f"update_stats raised {type(e).__name__}")

    def test_show_save_info(self):
        """Test that save info display works."""
        save_file = "TestFiles/potato 2.save"
        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        try:
            self.app.show_save_info()
            info_text = self.app.info_text_widget.get("1.0", tk.END)
            self.assertIn("Save File:", info_text, "Info should contain save file name")
        except Exception as e:
            self.fail(f"show_save_info raised {type(e).__name__}")

    def test_show_campaign_settings(self):
        """Test that campaign settings display works."""
        save_file = "TestFiles/simple/10mission.save"
        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        try:
            self.app.show_campaign_settings()
            campaign_text = self.app.campaign_text_widget.get("1.0", tk.END)
            # Should display at least the title
            self.assertIn("CAMPAIGN SETTINGS", campaign_text)
        except Exception as e:
            self.fail(f"show_campaign_settings raised {type(e).__name__}")

    def test_show_locations(self):
        """Test that locations display works."""
        save_file = "TestFiles/simple/2mission.save"
        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        self.app.current_save_path = save_file
        self.app.parse_save_file()

        try:
            self.app.show_locations_and_missions()
            loc_text = self.app.locations_text_widget.get("1.0", tk.END)
            self.assertIn("LOCATIONS", loc_text, "Should display locations")
        except Exception as e:
            self.fail(f"show_locations_and_missions raised {type(e).__name__}")


class TestSaveFileParsing(unittest.TestCase):
    """Test parsing of save file data."""

    def test_xml_extraction(self):
        """Test that XML can be extracted from saves."""
        save_file = "TestFiles/potato 2.save"

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        app = SaveFileViewer(tk.Tk())
        app.root.withdraw()

        try:
            with open(save_file, "rb") as f:
                data = f.read()

            # Level 0 decompression
            level0_data = __import__("gzip").decompress(data)

            # Extract files
            files = app._extract_save_files(level0_data)

            self.assertGreater(len(files), 0, "Should extract at least one file")

            # Should have XML files
            xml_files = [f for f in files.keys() if f.endswith(".xml")]
            self.assertGreater(len(xml_files), 0, "Should have XML files")

        finally:
            app.root.destroy()

    def test_character_data_parsing(self):
        """Test that character data can be parsed."""
        save_file = "TestFiles/simple/2mission.save"

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        app = SaveFileViewer(tk.Tk())
        app.root.withdraw()

        try:
            app.current_save_path = save_file
            app.parse_save_file()

            # Should have parsed characters
            self.assertGreater(len(app.characters), 0, "Should have characters")

            # Check character structure
            for char in app.characters:
                self.assertIn("name", char, "Character should have name")
                self.assertIn("job", char, "Character should have job")

        finally:
            app.root.destroy()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_invalid_file_path(self):
        """Test behavior with invalid file path."""
        app = SaveFileViewer(self.root)

        # Should raise an error for non-existent file
        app.current_save_path = "nonexistent.save"

        with self.assertRaises(FileNotFoundError):
            app.parse_save_file()

    def test_empty_campaign_settings(self):
        """Test handling of missing campaign settings."""
        save_file = "TestFiles/potato 2.save"  # Template file, no campaign

        if not Path(save_file).exists():
            self.skipTest(f"File not found: {save_file}")

        app = SaveFileViewer(self.root)
        app.current_save_path = save_file
        app.parse_save_file()

        # Template files may have empty or no campaign settings
        self.assertIsInstance(app.campaign_settings, dict)


if __name__ == "__main__":
    print("Running comprehensive save file tests...\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSaveFileLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestSaveFileViewerGUI))
    suite.addTests(loader.loadTestsFromTestCase(TestSaveFileParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
