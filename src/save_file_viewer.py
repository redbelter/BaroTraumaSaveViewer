#!/usr/bin/env python3
"""
Comprehensive Save File Viewer - Single Tool for All Save File Analysis

Features:
- Browse and select .save files from any location
- Auto-detect binary compression format (gzip streams)
- Extract XML content from nested gzip archives
- Parse character data directly from the save file
- Display campaign settings (MaxMissionCount, world settings)
- Show locations and destinations
- Export to matching XML format
- GUI interface with multiple tabs
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import re


class SaveFileViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Submarine Save File Viewer")
        self.root.geometry("1000x700")

        # Current state
        self.current_save_path = None
        self.characters = []
        self.sub_info = {}
        self.campaign_settings = {}
        self.locations = []
        self.destinations = []

        # Menu reference for later use
        self.file_menu = None

        # Build UI
        self.build_ui()

    def build_ui(self):
        """Build the complete user interface"""

        # Menu bar
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Open Save File", command=self.load_and_parse_save_file
        )
        file_menu.add_separator()
        self.export_menu_item = file_menu.add_command(
            label="Export to XML", command=self.export_to_xml, state="disabled"
        )
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.root.config(menu=menubar)

        # Store reference to file_menu for later use
        self.file_menu = file_menu

        # Export menu is at index 2 (0=Open, 1=separator, 2=Export)
        self.export_menu_index = 2

        # Main notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Character List
        char_frame = ttk.Frame(notebook)
        notebook.add(char_frame, text="Characters")

        # Tab 2: Campaign Settings
        campaign_frame = ttk.Frame(notebook)
        notebook.add(campaign_frame, text="Campaign Settings")

        # Tab 3: Submarine Info
        submarine_frame = ttk.Frame(notebook)
        notebook.add(submarine_frame, text="Submarine Info")

        # Tab 4: Locations & Destinations
        locations_frame = ttk.Frame(notebook)
        notebook.add(locations_frame, text="Locations & Missions")

        # Tab 5: Save File Info
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Save File Info")

        # Tab 6: XML Preview
        xml_frame = ttk.Frame(notebook)
        notebook.add(xml_frame, text="XML Preview")

        # ========== CHARACTERS TAB ==========

        # Controls
        control_frame = ttk.Frame(char_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Filter by Job:").pack(side=tk.LEFT, padx=(0, 5))

        self.job_filter_var = tk.StringVar(value="All")
        self.job_combo = ttk.Combobox(
            control_frame, textvariable=self.job_filter_var, width=20
        )
        self.job_combo.pack(side=tk.LEFT)
        self.job_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.refresh_characters_table()
        )

        # Split pane for table and stats
        char_pane = ttk.PanedWindow(char_frame, orient=tk.HORIZONTAL)
        char_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Character table frame
        table_container = ttk.LabelFrame(char_pane, text="Crew Manifest", padding="5")
        char_pane.add(table_container, weight=1)

        columns = ("ID", "Name", "Job", "Status", "Condition", "Position")
        self.char_tree = ttk.Treeview(
            table_container, columns=columns, show="headings", height=20
        )
        self.char_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(
            table_container, orient="vertical", command=self.char_tree.yview
        )
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_tree.configure(yscrollcommand=vsb.set)

        for col in columns:
            self.char_tree.heading(col, text=col, anchor=tk.W)
            if col == "ID":
                self.char_tree.column(col, width=60, anchor=tk.W)
            elif col == "Position":
                self.char_tree.column(col, width=150, anchor=tk.W)
            elif col == "Status":
                self.char_tree.column(col, width=80, anchor=tk.W)
            else:
                self.char_tree.column(col, width=120, anchor=tk.W)

        self.char_tree.bind("<<TreeviewSelect>>", self.on_char_select)

        # Statistics frame
        stats_frame = ttk.LabelFrame(char_pane, text="Statistics", padding="10")
        char_pane.add(stats_frame, weight=0)

        self.stats_text = scrolledtext.ScrolledText(
            stats_frame, height=15, wrap=tk.WORD, state="disabled"
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Character detail frame
        detail_frame = ttk.LabelFrame(char_frame, text="Character Detail", padding="10")
        detail_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        self.detail_text = scrolledtext.ScrolledText(
            detail_frame, height=8, wrap=tk.WORD
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.configure(state="disabled")

        # Tab 7: Hulls & Structure
        structure_frame = ttk.Frame(notebook)
        notebook.add(structure_frame, text="Hulls & Structure")

        # Tab 8: Items & Inventory
        items_frame = ttk.Frame(notebook)
        notebook.add(items_frame, text="Items & Inventory")

        # ========== HULLS & STRUCTURE TAB ==========
        structure_notebook = ttk.Notebook(structure_frame)
        structure_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        hulls_frame = ttk.Frame(structure_notebook)
        structure_notebook.add(hulls_frame, text="Hulls")

        columns = ("ID", "Name", "Health%", "Integrity", "Damage")
        self.hulls_tree = ttk.Treeview(
            hulls_frame, columns=columns, show="headings", height=15
        )
        self.hulls_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for col in columns:
            self.hulls_tree.heading(col, text=col, anchor=tk.W)
            if col == "ID":
                self.hulls_tree.column(col, width=60, anchor=tk.W)
            elif col == "Name":
                self.hulls_tree.column(col, width=140, anchor=tk.W)
            elif col in ("Health%", "Integrity", "Damage"):
                self.hulls_tree.column(col, width=80, anchor=tk.W)

        structures_frame = ttk.Frame(structure_notebook)
        structure_notebook.add(structures_frame, text="Structures")

        columns = ("ID", "Name", "Type", "Position", "Size")
        self.structures_tree = ttk.Treeview(
            structures_frame, columns=columns, show="headings", height=15
        )
        self.structures_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for col in columns:
            self.structures_tree.heading(col, text=col, anchor=tk.W)
            if col == "ID":
                self.structures_tree.column(col, width=60, anchor=tk.W)
            elif col == "Name":
                self.structures_tree.column(col, width=140, anchor=tk.W)
            elif col == "Type":
                self.structures_tree.column(col, width=120, anchor=tk.W)
            elif col == "Position":
                self.structures_tree.column(col, width=200, anchor=tk.W)
            elif col == "Size":
                self.structures_tree.column(col, width=80, anchor=tk.W)

        gaps_frame = ttk.Frame(structure_notebook)
        structure_notebook.add(gaps_frame, text="Gaps")

        columns = ("ID", "Position", "Size")
        self.gaps_tree = ttk.Treeview(
            gaps_frame, columns=columns, show="headings", height=15
        )
        self.gaps_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        for col in columns:
            self.gaps_tree.heading(col, text=col, anchor=tk.W)
            if col == "ID":
                self.gaps_tree.column(col, width=60, anchor=tk.W)
            elif col == "Position":
                self.gaps_tree.column(col, width=220, anchor=tk.W)
            elif col == "Size":
                self.gaps_tree.column(col, width=100, anchor=tk.W)

        # ========== ITEMS & INVENTORY TAB ==========
        items_control_frame = ttk.Frame(items_frame)
        items_control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(items_control_frame, text="Filter by Type:").pack(
            side=tk.LEFT, padx=(0, 5)
        )

        self.item_filter_var = tk.StringVar(value="All")
        item_types = [
            "All",
            "duffelbag",
            "weapon",
            "ammo",
            "food",
            "medical",
            "equipment",
        ]
        self.item_combo = ttk.Combobox(
            items_control_frame,
            textvariable=self.item_filter_var,
            values=item_types,
            width=20,
        )
        self.item_combo.pack(side=tk.LEFT)
        self.item_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.refresh_items_table()
        )

        # Split pane for items table and details
        items_pane = ttk.PanedWindow(items_frame, orient=tk.HORIZONTAL)
        items_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Items table frame
        items_table_container = ttk.LabelFrame(items_pane, text="Items", padding="5")
        items_pane.add(items_table_container, weight=1)

        columns = ("ID", "Identifier", "Type", "Position", "Condition")
        self.items_tree = ttk.Treeview(
            items_table_container, columns=columns, show="headings", height=20
        )
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb_items = ttk.Scrollbar(
            items_table_container, orient="vertical", command=self.items_tree.yview
        )
        vsb_items.pack(side=tk.RIGHT, fill=tk.Y)
        self.items_tree.configure(yscrollcommand=vsb_items.set)

        for col in columns:
            self.items_tree.heading(col, text=col, anchor=tk.W)
            if col == "ID":
                self.items_tree.column(col, width=60, anchor=tk.W)
            elif col == "Identifier":
                self.items_tree.column(col, width=150, anchor=tk.W)
            elif col == "Type":
                self.items_tree.column(col, width=120, anchor=tk.W)
            elif col == "Position":
                self.items_tree.column(col, width=180, anchor=tk.W)
            elif col == "Condition":
                self.items_tree.column(col, width=80, anchor=tk.W)

        self.items_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # Item detail frame
        item_detail_frame = ttk.LabelFrame(
            items_pane, text="Item Details", padding="10"
        )
        items_pane.add(item_detail_frame, weight=0)

        self.item_detail_text = scrolledtext.ScrolledText(
            item_detail_frame, height=20, wrap=tk.WORD
        )
        self.item_detail_text.pack(fill=tk.BOTH, expand=True)
        self.item_detail_text.configure(state="disabled")

        # ========== CAMPAIGN SETTINGS TAB ==========
        campaign_text = scrolledtext.ScrolledText(campaign_frame, wrap=tk.WORD)
        campaign_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.campaign_text_widget = campaign_text

        # ========== SUBMARINE INFO TAB ==========
        submarine_text = scrolledtext.ScrolledText(submarine_frame, wrap=tk.WORD)
        submarine_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.submarine_text_widget = submarine_text

        # ========== LOCATIONS & MISSIONS TAB ==========
        locations_text = scrolledtext.ScrolledText(locations_frame, wrap=tk.WORD)
        locations_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.locations_text_widget = locations_text

        # ========== SAVE FILE INFO TAB ==========
        info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_text_widget = info_text

        # ========== XML PREVIEW TAB ==========
        xml_text = scrolledtext.ScrolledText(xml_frame, wrap=tk.NONE)
        xml_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        xml_text.configure(state="disabled")
        self.xml_text_widget = xml_text

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Select a save file to begin")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_save_file(self):
        """Open file dialog to select a .save file"""
        filename = filedialog.askopenfilename(
            title="Select Save File",
            filetypes=[("Save Files", "*.save"), ("All Files", "*.*")],
        )
        if filename:
            self.current_save_path = filename
            self.status_var.set(f"Selected: {Path(filename).name}")

    def load_and_parse_save_file(self):
        """Open file dialog and immediately load/parse the selected save file"""
        filename = filedialog.askopenfilename(
            title="Select Save File",
            filetypes=[("Save Files", "*.save"), ("All Files", "*.*")],
        )
        if not filename:
            return

        self.current_save_path = filename

        try:
            self.status_var.set(f"Loading: {Path(filename).name}...")
            self.root.update()

            # Parse the save file
            self.parse_save_file()

            # Update UI
            self.refresh_characters_table()
            self.show_campaign_settings()
            self.show_submarine_info()
            self.show_locations_and_missions()
            self.show_save_info()
            self.show_xml_preview()

            # Enable export menu using stored reference and index
            if hasattr(self, "file_menu") and self.file_menu:
                self.file_menu.entryconfig(self.export_menu_index, state="normal")

            self.status_var.set(
                f"Loaded: {Path(filename).name} - {len(self.characters)} characters found"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def load_selected_save(self):
        """Load and parse the currently selected save file"""
        if not self.current_save_path or not Path(self.current_save_path).exists():
            messagebox.showerror("Error", "Please select a valid save file first!")
            return

        try:
            self.status_var.set(f"Loading: {Path(self.current_save_path).name}...")
            self.root.update()

            # Parse the save file
            self.parse_save_file()

            # Update UI
            self.refresh_characters_table()
            self.show_campaign_settings()
            self.show_submarine_info()
            self.show_locations_and_missions()
            self.show_save_info()
            self.show_xml_preview()

            # Enable export menu using stored reference and index
            if hasattr(self, "file_menu") and self.file_menu:
                self.file_menu.entryconfig(self.export_menu_index, state="normal")

            self.status_var.set(
                f"Loaded: {Path(self.current_save_path).name} - {len(self.characters)} characters found"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def refresh_current_file(self):
        """Re-parse and refresh the currently loaded save file"""
        if not self.current_save_path or not Path(self.current_save_path).exists():
            messagebox.showerror("Error", "No valid save file loaded!")
            return

        try:
            self.status_var.set(f"Refreshing: {Path(self.current_save_path).name}...")
            self.root.update()

            self.parse_save_file()
            self.refresh_characters_table()
            self.show_campaign_settings()
            self.show_submarine_info()
            self.show_locations_and_missions()
            self.show_save_info()
            self.show_xml_preview()
            self.status_var.set(f"Refreshed: {Path(self.current_save_path).name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh:\n{str(e)}")

    def parse_save_file(self):
        """Parse the binary save file and extract all data"""

        # Read original compressed file
        with open(self.current_save_path, "rb") as f:
            original_data = f.read()

        self.save_info = {
            "filename": Path(self.current_save_path).name,
            "original_size": len(original_data),
            "decompressed_size": 0,
        }

        # Level 0 decompression (outer gzip)
        level0_decompressed = gzip.decompress(original_data)
        self.save_info["decompressed_size"] = len(level0_decompressed)

        # Extract all files from the decompressed data
        files = self._extract_save_files(level0_decompressed)

        if not files:
            raise ValueError("No valid files found in save file!")

        self.xml_content = ""
        root = None

        # Try to find submarine and campaign XML files
        for filename, file_content in files.items():
            if filename.endswith(".xml"):
                xml_str = file_content.decode("utf-8", errors="ignore")

                # Try submarine XML
                if "submarine" in filename.lower():
                    self.xml_content = xml_str
                    try:
                        root = ET.fromstring(xml_str)
                        self._parse_submarine_xml(root)
                    except:
                        pass

                # Try gamesession or campaign XML
                if "gamesession" in filename.lower():
                    try:
                        campaign_root = ET.fromstring(xml_str)
                        # Only parse campaign data if this appears to be a campaign save
                        # (check for map element or MultiPlayerCampaign)
                        if (
                            campaign_root.find(".//map") is not None
                            or campaign_root.find(".//MultiPlayerCampaign") is not None
                        ):
                            self._parse_campaign_xml(campaign_root)
                    except:
                        pass

            # Handle .sub files (gzipped submarine XML)
            elif filename.endswith(".sub"):
                try:
                    # Decompress the .sub file
                    decompressed_xml = gzip.decompress(file_content)
                    xml_str = decompressed_xml.decode("utf-8", errors="ignore")

                    # Try to parse as submarine XML
                    test_root = ET.fromstring(xml_str)
                    if test_root.tag == "Submarine":
                        self.xml_content = xml_str
                        root = test_root
                        self._parse_submarine_xml(root)
                        # Don't break here - continue processing other files for campaign data

                except:
                    continue

        # If we still don't have root, try to find any valid submarine XML
        if root is None:
            for filename, file_content in files.items():
                if filename.endswith(".xml"):
                    xml_str = file_content.decode("utf-8", errors="ignore")
                    try:
                        test_root = ET.fromstring(xml_str)
                        if test_root.tag == "Submarine":
                            self.xml_content = xml_str
                            root = test_root
                            self._parse_submarine_xml(root)
                            break
                    except:
                        continue

        if root is None:
            raise ValueError("No valid Submarine XML found in save file!")

        # Try to find and parse corresponding CharacterData file for living characters
        save_path = Path(self.current_save_path)
        character_data_path = save_path.parent / f"{save_path.stem}_CharacterData.xml"

        # If not found in same directory, check subdirectories
        if not character_data_path.exists():
            for subdir in save_path.parent.iterdir():
                if subdir.is_dir():
                    candidate = subdir / f"{save_path.stem}_CharacterData.xml"
                    if candidate.exists():
                        character_data_path = candidate
                        break

        living_characters = []
        if character_data_path.exists():
            living_characters = self._parse_character_data_file(
                str(character_data_path)
            )

        # Combine living characters with stored characters
        # Prioritize living characters over duffelbag characters with the same name
        living_names = {char["name"] for char in living_characters}
        filtered_stored = [
            char for char in self.characters if char["name"] not in living_names
        ]

        self.characters = living_characters + filtered_stored

    def _extract_save_files(self, data):
        """Extract all files from decompressed save data

        File format:
        - 4 bytes: filename length (int32)
        - N*2 bytes: filename in UTF-16LE
        - 4 bytes: file content length (int32)
        - M bytes: file content
        """
        files = {}
        i = 0

        while i < len(data):
            # Check if we have enough bytes for length field
            if i + 4 > len(data):
                break

            # Read filename length
            name_length = int.from_bytes(data[i : i + 4], byteorder="little")
            i += 4

            # Sanity check - filename shouldn't be absurdly long
            if name_length < 0 or name_length > 10000:
                break

            # Read filename (UTF-16LE)
            if i + name_length * 2 > len(data):
                break

            try:
                filename = data[i : i + name_length * 2].decode("utf-16-le")
                i += name_length * 2
            except:
                break

            # Read file content length
            if i + 4 > len(data):
                break

            content_length = int.from_bytes(data[i : i + 4], byteorder="little")
            i += 4

            # Sanity check - file shouldn't be absurdly large
            if content_length < 0 or content_length > 10000000:
                break

            # Read file content
            if i + content_length > len(data):
                break

            file_content = data[i : i + content_length]
            i += content_length

            files[filename] = file_content

        return files

    def _parse_submarine_xml(self, root):
        """Parse submarine XML element"""
        self.sub_info = {
            "name": root.get("name", "Unknown"),
            "type": root.get("type", "Unknown"),
            "class": root.get("class", "Unknown"),
            "tier": root.get("tier", "Unknown"),
            "gameversion": root.get("gameversion", "Unknown"),
            "dimensions": root.get("dimensions", "Unknown"),
            "cargocapacity": root.get("cargocapacity", "Unknown"),
            "price": root.get("price", "Unknown"),
            "tags": root.get("Tags", "Unknown"),
        }

        # Extract items from submarine XML
        self.items = []
        for item in root.findall(".//Item"):
            item_id = item.get("ID", "Unknown")
            identifier = item.get("identifier", "unknown")

        # Extract hulls
        self.hulls = []
        for hull in root.findall(".//Hull"):
            health_pct = float(hull.get("healthpercentage", "100"))
            integrity = int(float(hull.get("integrity", "100")))

            self.hulls.append(
                {
                    "id": hull.get("ID", "Unknown"),
                    "name": hull.get("name", "Hull"),
                    "health_pct": f"{health_pct:.2f}%",
                    "integrity": integrity,
                    "damage": 100 - integrity,
                }
            )

        # Extract structures
        self.structures = []
        for struct in root.findall(".//Structure"):
            rect = struct.get("rect", "")
            size_match = re.search(r'size="([^"]*)"', rect)
            size = size_match.group(1) if size_match else "Unknown"

            self.structures.append(
                {
                    "id": struct.get("ID", "Unknown"),
                    "name": struct.get("name", "Structure"),
                    "type": struct.get("type", "custom"),
                    "position": rect,
                    "size": size,
                }
            )

        # Extract gaps
        self.gaps = []
        for gap in root.findall(".//Gap"):
            rect = gap.get("rect", "")
            size_match = re.search(r'size="([^"]*)"', rect)
            size = size_match.group(1) if size_match else "Unknown"

            self.gaps.append(
                {
                    "id": gap.get("ID", "Unknown"),
                    "position": rect,
                    "size": size,
                }
            )



            item_type = "custom"
            if "_" in identifier:
                parts = identifier.split("_")
                if len(parts) >= 2:
                    item_type = parts[1].lower()

            self.items.append(
                {
                    "id": item_id,
                    "identifier": identifier,
                    "type": item_type,
                    "position": item.get("rect", ""),
                    "condition": f"{float(item.get('conditionpercentage', '100')):.2f}%",
                    "tags": item.get("Tags", ""),
                    "parent_id": item.get("parentid", ""),
                }
            )

    def _parse_campaign_xml(self, root):
        """Parse campaign/gamesession XML element"""
        # Extract campaign settings (could be at root level or nested)
        campaign_elem = root.find(".//campaignsettings")
        if campaign_elem is not None:
            self.campaign_settings = dict(campaign_elem.attrib)
        else:
            # Also try finding it as direct child
            for elem in root:
                if elem.tag == "campaignsettings":
                    self.campaign_settings = dict(elem.attrib)
                    break

        # Extract locations from the map element within MultiPlayerCampaign
        self.locations = []
        # Look for locations in the map element
        map_elem = root.find(".//map")
        if map_elem is not None:
            locations = map_elem.findall(".//location")
            for location in locations:
                self.locations.append(
                    {
                        "name": location.get("name", "Unknown"),
                        "type": location.get("type", "Unknown"),
                        "biome": location.get("biome", "Unknown"),
                        "position": location.get("position", "Unknown"),
                    }
                )

        # If no locations found in map, try the old method as fallback
        if not self.locations:
            locations = root.findall(".//location")
            for location in locations:
                self.locations.append(
                    {
                        "name": location.get("name", "Unknown"),
                        "type": location.get("type", "Unknown"),
                        "biome": location.get("biome", "Unknown"),
                        "position": location.get("position", "Unknown"),
                    }
                )

        # Extract characters from the campaign (not from submarine duffelbags for campaign saves)
        # Campaign characters are stored differently than submarine template characters
        campaign_characters = []
        characters = root.findall(".//Character")
        for char in characters:
            # Campaign characters have different attributes than submarine characters
            char_data = {
                "id": char.get("id", "0"),
                "name": char.get("name", "Unknown"),
                "job": char.get("job", "Unknown"),
                "condition": "100%",  # Campaign saves may not store condition
                "rect": "",  # No position data in campaign saves
                "status": "Campaign",  # Add status field
            }
            campaign_characters.append(char_data)

        # If we found campaign characters and no submarine characters, use them
        if campaign_characters and not self.characters:
            self.characters = campaign_characters

        # Extract destination indices from character data
        self.destinations = []
        for char in root.findall(".//Character"):
            dest_idx = char.get("destinationindex", None)
            if dest_idx:
                try:
                    idx = int(dest_idx)
                    if idx < len(self.locations):
                        dest_name = self.locations[idx].get("name", f"Location {idx}")
                        if dest_name not in [d.get("name") for d in self.destinations]:
                            self.destinations.append({"index": idx, "name": dest_name})
                except (ValueError, IndexError, TypeError):
                    pass

    def _parse_character_data_file(self, filepath):
        """Parse CharacterData XML file for living characters"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            living_characters = []
            for char_campaign in root.findall(".//CharacterCampaignData"):
                char_elem = char_campaign.find(".//Character")
                if char_elem is not None:
                    # Check if character is alive (not permanently dead)
                    permanently_dead = (
                        char_elem.get("permanentlydead", "false").lower() == "true"
                    )
                    if not permanently_dead:
                        # Get job from job element
                        job_elem = char_elem.find(".//job")
                        job_name = (
                            job_elem.get("name", "Unknown")
                            if job_elem is not None
                            else "Unknown"
                        )

                        char_data = {
                            "id": char_campaign.get(
                                "name", "Unknown"
                            ),  # Use account name as ID
                            "name": char_elem.get("name", "Unknown"),
                            "job": job_name,
                            "condition": "Alive",  # Living characters don't have condition percentage
                            "rect": "Living Crew",  # Indicate this is a living character
                            "status": "Living",  # Add status field
                        }
                        living_characters.append(char_data)

            return living_characters

        except Exception as e:
            print(f"Warning: Could not parse CharacterData file {filepath}: {e}")
            return []

    def refresh_characters_table(self):
        """Refresh the character table with current filter"""
        # Clear existing items
        for item in self.char_tree.get_children():
            self.char_tree.delete(item)

        # Get current filter
        job_filter = self.job_filter_var.get()

        # Filter characters
        if job_filter != "All":
            filtered_chars = [c for c in self.characters if c["job"] == job_filter]
        else:
            filtered_chars = list(self.characters)

        # Insert items
        for char in sorted(
            filtered_chars, key=lambda x: (x.get("status", ""), str(x["id"]))
        ):
            item_id = self.char_tree.insert(
                "",
                tk.END,
                values=(
                    char["id"],
                    char["name"],
                    char["job"],
                    char.get("status", "Unknown"),
                    char["condition"],
                    char["rect"],
                ),
            )

            # Tag low condition characters
            try:
                condition_val = float(char["condition"].rstrip("%"))
                if condition_val < 50:
                    self.char_tree.item(item_id, tags=("low_condition",))
                elif condition_val < 80:
                    self.char_tree.item(item_id, tags=("medium_condition",))
            except ValueError:
                pass

        # Configure tags
        self.char_tree.tag_configure(
            "low_condition", foreground="red", font=("Arial", 9, "bold")
        )
        self.char_tree.tag_configure("medium_condition", foreground="orange")

        # Update stats
        self.update_stats()

    def update_stats(self):
        """Update statistics display"""
        unique_names = len(set(c["name"] for c in self.characters))

        job_counts = defaultdict(int)
        for char in self.characters:
            job_counts[char["job"]] += 1

        stats = f"""Save File Information:
-------------------
File: {self.save_info.get("filename", "Unknown")}
Original Size: {self.save_info.get("original_size", 0):,} bytes
Decompressed Size: {self.save_info.get("decompressed_size", 0):,} bytes
Main Stream Position: {self.save_info.get("main_stream_pos", 0)}
Main Stream Size: {self.save_info.get("main_stream_size", 0):,} bytes

Submarine Information:
---------------------
Name: {self.sub_info.get("name", "Unknown")}
Type: {self.sub_info.get("type", "Unknown")}
Class: {self.sub_info.get("class", "Unknown")}
Tier: {self.sub_info.get("tier", "Unknown")}
Game Version: {self.sub_info.get("gameversion", "Unknown")}

Crew Statistics:
---------------
Total Characters: {len(self.characters)}
Unique Names: {unique_names}
Jobs: {len(job_counts)}

Characters by Job:
------------------
"""
        for job, count in sorted(job_counts.items()):
            stats += f"  {job}: {count}\n"

        self.stats_text.configure(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats)
        self.stats_text.configure(state="disabled")

    def show_save_info(self):
        """Show save file information"""
        info = f"""Save File: {self.save_info.get("filename", "Unknown")}

Compression:
-----------
Original Size: {self.save_info.get("original_size", 0):,} bytes
Level 0 Decompressed: {self.save_info.get("decompressed_size", 0):,} bytes
Main Stream Position: {self.save_info.get("main_stream_pos", 0)}
Main Stream Size: {self.save_info.get("main_stream_size", 0):,} bytes

Submarine Details:
-----------------
Name: {self.sub_info.get("name", "Unknown")}
Type: {self.sub_info.get("type", "Unknown")}
Class: {self.sub_info.get("class", "Unknown")}
Tier: {self.sub_info.get("tier", "Unknown")}

Character Count: {len(self.characters)} crew members found
"""

        self.info_text_widget.configure(state="normal")
        self.info_text_widget.delete(1.0, tk.END)
        self.info_text_widget.insert(tk.END, info)
        self.info_text_widget.configure(state="disabled")

    def show_campaign_settings(self):
        """Show campaign settings information"""
        campaign_text = "CAMPAIGN SETTINGS\n" + "=" * 60 + "\n\n"

        if not self.campaign_settings:
            campaign_text += "No campaign settings found in this save file.\n"
        else:
            for key, value in sorted(self.campaign_settings.items()):
                # Format key names nicely
                display_key = key.replace("_", " ").title() if "_" in key else key
                campaign_text += f"{display_key:35} {value}\n"

        self.campaign_text_widget.configure(state="normal")
        self.campaign_text_widget.delete(1.0, tk.END)
        self.campaign_text_widget.insert(tk.END, campaign_text)
        self.campaign_text_widget.configure(state="disabled")

    def show_submarine_info(self):
        """Show complete submarine information"""
        sub_text = "SUBMARINE INFORMATION\n" + "=" * 60 + "\n\n"

        for key, value in sorted(self.sub_info.items()):
            display_key = key.replace("_", " ").title() if "_" in key else key
            # Truncate very long values
            if isinstance(value, str) and len(value) > 100:
                value = value[:97] + "..."
            sub_text += f"{display_key:35} {value}\n"

        self.submarine_text_widget.configure(state="normal")
        self.submarine_text_widget.delete(1.0, tk.END)
        self.submarine_text_widget.insert(tk.END, sub_text)
        self.submarine_text_widget.configure(state="disabled")

    def show_locations_and_missions(self):
        """Show locations and mission destinations"""
        loc_text = "LOCATIONS AND MISSIONS\n" + "=" * 70 + "\n"

        # Summary stats
        loc_text += f"\nTOTAL LOCATIONS: {len(self.locations)}\n"
        loc_text += f"ACTIVE MISSIONS: {len(self.destinations)}\n"
        loc_text += "-" * 70 + "\n"

        if not self.locations:
            loc_text += "\nNo locations found in this save file.\n\n"
            loc_text += "This appears to be a SUBMARINE TEMPLATE file\n"
            loc_text += (
                "(contains only submarine configuration, no world/campaign data)\n\n"
            )
            loc_text += "SUBMARINE TEMPLATE FILES contain:\n"
            loc_text += "  • Submarine structure (Items, Structures, Hulls, Gaps)\n"
            loc_text += "  • Crew quarters and equipment configuration\n"
            loc_text += "  \n"
            loc_text += "CAMPAIGN SAVE FILES contain:\n"
            loc_text += "  • All of the above\n"
            loc_text += "  • World locations with names, types, and positions\n"
            loc_text += "  • Mission destinations (routes for crew to travel)\n"
            loc_text += "  • Campaign progress and crew experience\n"
            loc_text += "  \n"
            loc_text += (
                "Examples of campaign files: '2mission.save', '10mission.save'\n"
            )
            loc_text += "Examples of template files: 'potato 2.save', 'grav.save'\n"
        else:
            # Create a set of destination indices for quick lookup
            dest_indices = set(d["index"] for d in self.destinations)

            # Display locations with details
            loc_text += "\nLOCATIONS:\n"
            loc_text += "-" * 70 + "\n"
            for i, loc in enumerate(self.locations):
                # Highlight locations that are active mission destinations
                mission_marker = " ← MISSION DESTINATION" if i in dest_indices else ""
                loc_text += f"\n[{i:2d}] {loc.get('name', 'Unknown')}{mission_marker}\n"
                loc_text += f"      Type:      {loc.get('type', 'Unknown')}\n"
                loc_text += f"      Biome:     {loc.get('biome', 'Unknown')}\n"
                loc_text += f"      Position:  {loc.get('position', 'Unknown')}\n"

        # Mission destinations section
        loc_text += "\n" + "=" * 70 + "\n"
        loc_text += "\nACTIVE MISSION DESTINATIONS:\n"
        loc_text += "-" * 70 + "\n"

        if not self.destinations:
            loc_text += "  [No crew members have active mission destinations]\n"
        else:
            # Group destinations by location
            dest_by_loc = {}
            for dest in self.destinations:
                idx = dest["index"]
                if idx not in dest_by_loc:
                    dest_by_loc[idx] = []
                dest_by_loc[idx].append(dest)

            # Display sorted by location index
            for idx in sorted(dest_by_loc.keys()):
                loc_name = (
                    self.locations[idx].get("name", f"Location {idx}")
                    if idx < len(self.locations)
                    else f"Location {idx}"
                )
                crew_count = len(dest_by_loc[idx])
                loc_text += f"\n  Location [{idx}]: {loc_name} ({crew_count} crew member{'s' if crew_count != 1 else ''})\n"

        # Additional information
        loc_text += "\n" + "=" * 70 + "\n"
        loc_text += "\nNOTES:\n"
        loc_text += "-" * 70 + "\n"

        if self.locations:
            # Calculate some statistics
            biome_types = {}
            location_types = {}
            for loc in self.locations:
                biome = loc.get("biome", "Unknown")
                loc_type = loc.get("type", "Unknown")
                biome_types[biome] = biome_types.get(biome, 0) + 1
                location_types[loc_type] = location_types.get(loc_type, 0) + 1

            loc_text += f"\nLocation Types: {', '.join(f'{k}({v})' for k, v in sorted(location_types.items()))}\n"
            loc_text += f"Biome Distribution: {', '.join(f'{k}({v})' for k, v in sorted(biome_types.items()))}\n"

            # Info about mission destinations
            if self.destinations:
                total_crew_with_missions = len(self.destinations)
                total_crew = len(self.characters) if hasattr(self, "characters") else 0
                if total_crew > 0:
                    pct = (total_crew_with_missions / total_crew) * 100
                    loc_text += f"\nCrew Status: {total_crew_with_missions}/{total_crew} crew members ({pct:.1f}%) have active missions\n"
                else:
                    loc_text += f"\nCrew with missions: {total_crew_with_missions}\n"
        else:
            loc_text += "\n(No location data available in this save file)\n"

        self.locations_text_widget.configure(state="normal")
        self.locations_text_widget.delete(1.0, tk.END)
        self.locations_text_widget.insert(tk.END, loc_text)
        self.locations_text_widget.configure(state="disabled")

    def show_xml_preview(self):
        """Show XML preview with syntax highlighting"""
        # Format XML with proper indentation
        try:
            root = ET.fromstring(self.xml_content)
            # Pretty print with limited depth to keep preview readable
            xml_preview = ET.tostring(root, encoding="unicode")
            # Add some basic formatting
            xml_preview = self._format_xml_pretty(
                xml_preview[:5000]
            )  # First 5000 chars
            xml_preview += "\n\n[... (truncated for readability) ...]\n"
        except:
            xml_preview = self.xml_content[:5000]

        self.xml_text_widget.configure(state="normal")
        self.xml_text_widget.delete(1.0, tk.END)
        self.xml_text_widget.insert(tk.END, xml_preview)
        self.xml_text_widget.configure(state="disabled")

    def _format_xml_pretty(self, xml_str):
        """Simple XML formatting for display"""
        # Add newlines after > and before <
        formatted = re.sub(r">\s*<", ">\n<", xml_str)
        # Add indentation
        lines = formatted.split("\n")
        result = []
        indent_level = 0
        for line in lines:
            if line.startswith("</"):
                indent_level = max(0, indent_level - 1)
            result.append("  " * indent_level + line)
            if (
                line.startswith("<")
                and not line.startswith("</")
                and not line.endswith("/>")
            ):
                indent_level += 1
        return "\n".join(result[:100])  # Return first 100 lines

    def on_char_select(self, event):
        """Handle character selection"""
        selection = self.char_tree.selection()
        if not selection:
            return

        item = self.char_tree.item(selection[0])
        values = item["values"]

        if len(values) < 6:  # Updated for new Status column
            return

        char_id = values[0]  # Can be string or int now
        char_data = next(
            (c for c in self.characters if str(c["id"]) == str(char_id)), None
        )

        if not char_data:
            return

        status = char_data.get("status", "Unknown")
        if status == "Living":
            status_desc = "This is a living crew member."
        elif status == "In Duffelbag":
            status_desc = "This character is stored in a duffelbag container with their personal items."
        else:
            status_desc = f"Status: {status}"

        details = f"""
Character ID: {char_data["id"]}
Name: {char_data["name"]}
Job: {char_data["job"]}
Status: {status}
Condition: {char_data["condition"]}
Position: {char_data["rect"]}

Submarine Information:
  - Name: {self.sub_info.get("name", "Unknown")}
  - Type: {self.sub_info.get("type", "Unknown")}
  - Class: {self.sub_info.get("class", "Unknown")}
  - Tier: {self.sub_info.get("tier", "Unknown")}
  - Game Version: {self.sub_info.get("gameversion", "Unknown")}

{status_desc}
"""

        self.detail_text.configure(state="normal")
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, details)
        self.detail_text.configure(state="disabled")


    def on_item_select(self, event):
        """Handle item selection"""
        selection = self.items_tree.selection()
        if not selection:
            return

        item = self.items_tree.item(selection[0])
        values = item['values']

        if len(values) < 5:
            return

        item_id = values[0]
        item_data = next((i for i in self.items if str(i['id']) == str(item_id)), None)

        if not item_data:
            return

        status_desc = "This is an item in the submarine inventory."

        details = """
Item ID: {item_id}
Identifier: {item_data['identifier']}
Type: {item_data['type']}
Position: {item_data['position']}
Condition: {item_data['condition']}
Tags: {item_data.get('tags', 'None')}
Parent ID: {item_data.get('parent_id', 'None')}

Submarine Information:
  - Name: {self.sub_info.get('name', 'Unknown')}
  - Type: {self.sub_info.get('type', 'Unknown')}
  - Class: {self.sub_info.get('class', 'Unknown')}
  - Tier: {self.sub_info.get('tier', 'Unknown')}

{status_desc}
""".format(**locals())

        self.item_detail_text.configure(state="normal")
        self.item_detail_text.delete(1.0, tk.END)
        self.item_detail_text.insert(tk.END, details)
        self.item_detail_text.configure(state="disabled")




    def refresh_items_table(self):
        """Refresh the items table with current filter"""
        # Clear existing items
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        # Get current filter
        item_filter = self.item_filter_var.get()

        # Filter items
        if item_filter != "All":
            filtered_items = [i for i in self.items if i["type"] == item_filter]
        else:
            filtered_items = list(self.items)

        # Insert items
        for item in sorted(filtered_items, key=lambda x: (str(x["id"]))):
            item_id = self.items_tree.insert(
                "",
                tk.END,
                values=(
                    item["id"],
                    item["identifier"],
                    item["type"],
                    item.get("position", ""),
                    item["condition"],
                ),
            )


    def on_item_select(self, event):
        """Handle item selection"""
        selection = self.items_tree.selection()
        if not selection:
            return

        item = self.items_tree.item(selection[0])
        values = item['values']

        if len(values) < 5:
            return

        item_id = values[0]
        item_data = next((i for i in self.items if str(i['id']) == str(item_id)), None)

        if not item_data:
            return

        status_desc = "This is an item in the submarine inventory."

        details = """
Item ID: {item_id}
Identifier: {item_data['identifier']}
Type: {item_data['type']}
Position: {item_data['position']}
Condition: {item_data['condition']}
Tags: {item_data.get('tags', 'None')}
Parent ID: {item_data.get('parent_id', 'None')}

Submarine Information:
  - Name: {self.sub_info.get('name', 'Unknown')}
  - Type: {self.sub_info.get('type', 'Unknown')}
  - Class: {self.sub_info.get('class', 'Unknown')}
  - Tier: {self.sub_info.get('tier', 'Unknown')}

{status_desc}
""".format(**locals())

        self.item_detail_text.configure(state="normal")
        self.item_detail_text.delete(1.0, tk.END)
        self.item_detail_text.insert(tk.END, details)
        self.item_detail_text.configure(state="disabled")



    def refresh_hulls_table(self):
        """Refresh the hulls table"""
        for item in self.hulls_tree.get_children():
            self.hulls_tree.delete(item)

        for hull in sorted(self.hulls, key=lambda x: str(x["id"])):
            self.hulls_tree.insert(
                "",
                tk.END,
                values=(
                    hull["id"],
                    hull["name"],
                    hull["health_pct"],
                    hull["integrity"],
                    hull["damage"],
                ),
            )

    def refresh_structures_table(self):
        """Refresh the structures table"""
        for item in self.structures_tree.get_children():
            self.structures_tree.delete(item)

        for struct in sorted(self.structures, key=lambda x: str(x["id"])):
            self.structures_tree.insert(
                "",
                tk.END,
                values=(
                    struct["id"],
                    struct["name"],
                    struct["type"],
                    struct["position"],
                    struct.get("size", ""),
                ),
            )

    def refresh_gaps_table(self):
        """Refresh the gaps table"""
        for item in self.gaps_tree.get_children():
            self.gaps_tree.delete(item)

        for gap in sorted(self.gaps, key=lambda x: str(x["id"])):
            self.gaps_tree.insert(
                "",
                tk.END,
                values=(
                    gap["id"],
                    gap["position"],
                    gap.get("size", ""),
                ),
            )


    def export_to_xml(self):
        """Export character data to XML file"""
        if not self.characters:
            messagebox.showwarning("Warning", "No character data to export!")
            return

        # Generate XML
        root = ET.Element("CharacterData")

        sub_elem = ET.SubElement(root, "SubmarineInfo")
        for key, value in self.sub_info.items():
            sub_elem.set(key, str(value))

        chars_elem = ET.SubElement(root, "Characters")
        for char in sorted(
            self.characters, key=lambda x: (x.get("status", ""), str(x["id"]))
        ):
            char_elem = ET.SubElement(chars_elem, "Character")
            for key, value in char.items():
                char_elem.set(key, str(value))

        # Generate filename
        save_path = Path(self.current_save_path)
        xml_filename = save_path.stem + "_characters.xml"

        # Ask user where to save
        output_path = filedialog.asksaveasfilename(
            title="Export Character Data",
            defaultextension=".xml",
            initialfile=xml_filename,
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")],
        )

        if output_path:
            try:
                tree = ET.ElementTree(root)
                ET.indent(tree, space="  ")
                tree.write(output_path, encoding="UTF-8", xml_declaration=True)

                messagebox.showinfo(
                    "Success", f"Character data exported to:\n{output_path}"
                )
                self.status_var.set(f"Exported: {Path(output_path).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")


def main():
    root = tk.Tk()
    app = SaveFileViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
