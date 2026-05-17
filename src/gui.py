#!/usr/bin/env python3
"""Dear PyGui (v2.x) GUI for Barotrauma save file viewer — polished."""

from __future__ import annotations

import csv
import json
import io
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    print("Install dearpygui: pip install dearpygui")
    import sys
    sys.exit(1)

# ── Compatibility shim for mixed DPG versions ──
try:
    import dpg_compat  # noqa: F401
except ImportError:
    pass

try:
    from parser.data import SaveFile, Character, Item, Hull, Mission
    from parser.decode import parse_save
except ImportError:
    from data import SaveFile, Character, Item, Hull, Mission
    from decode import parse_save

# ── Color helpers ──

def _condition_color(pct: float) -> tuple[int, int, int]:
    """Return a green→yellow→red color based on percentage."""
    if pct >= 70:
        return (80, 220, 80)
    if pct >= 40:
        return (240, 200, 60)
    if pct >= 15:
        return (240, 140, 50)
    return (230, 60, 60)


def _status_color(char: Character) -> tuple[int, int, int]:
    if char.permanently_dead:
        return (180, 50, 50)
    if char.status == "Dead":
        return (180, 50, 50)
    cond_val = 100.0
    if char.condition.endswith("%"):
        try:
            cond_val = float(char.condition.rstrip("%"))
        except ValueError:
            pass
    return _condition_color(cond_val)


def _status_label(char: Character) -> str:
    if char.permanently_dead:
        return "☠ Dead"
    if char.status == "Dead":
        return "☠ Dead"
    if char.status == "Campaign":
        return "🏠 Campaign"
    if char.status == "In Duffelbag":
        return "📦 Duffelbag"
    return char.status


def _health_bar(h: Hull) -> str:
    if h.health_pct >= 80:
        return "🟩"
    if h.health_pct >= 40:
        return "🟨"
    return "🟥"


def _item_bar_pct(pct: float) -> str:
    if pct >= 80:
        return "▓▓▓▓▓▓▓▓▓▓"
    if pct >= 50:
        return "▓▓▓▓▓░░░░░"
    if pct >= 20:
        return "▓▓▓░░░░░░░"
    return "▓░░░░░░░░░"


# ── Recent saves ──

def _recent_path() -> Path:
    return Path.home() / ".openclaw" / "workspace" / "reverse-baro-recent.json"


def _load_recent() -> list[str]:
    p = _recent_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_recent(paths: list[str]) -> None:
    seen: list[str] = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    p = _recent_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(seen[:10], indent=2))


# ── Main app ──

class SaveViewer:
    """Dear PyGui v2 save file viewer."""

    def __init__(self) -> None:
        dpg.create_context()

        # State
        self.sf: SaveFile | None = None
        self.file_path: Path | None = None
        self.char_filter: str = "All"
        self.item_filter: str = "All"
        self.char_search: str = ""
        self.item_search: str = ""
        self._table_refs: dict[str, str | None] = {}

        # Viewport
        dpg.create_viewport(
            title="Barotrauma Save Viewer",
            width=1200,
            height=780,
            small_icon="icon.png",
            large_icon="icon.png",
        )
        dpg.set_viewport_width(1200)
        dpg.set_viewport_height(780)

        # Dark theme
        self._setup_theme()

        # Build UI
        self._build_menu()
        self._build_panels()
        self._build_statusbar()

        # Drag and drop on viewport
        self._setup_drop_target()

        # Keyboard shortcuts
        self._setup_shortcuts()

        print("Setting up Dear PyGui...")
        dpg.setup_dearpygui()
        print("Showing viewport...")
        dpg.show_viewport()
        print(f"Viewport width: {dpg.get_viewport_width()}, height: {dpg.get_viewport_height()}")
        # Give the viewport a moment to initialize
        time.sleep(0.1)
        
        # Load recent files after UI is ready
        self._refresh_recent_files()
        
        print("Starting Dear PyGui...")
        dpg.start_dearpygui()
        print("Destroying context...")
        dpg.destroy_context()

    # ── Theme ──

    def _setup_theme(self) -> None:
        # DPG 1.11.1 theme system doesn't support the old dpg.theme() context manager
        # approach used in earlier versions. Commenting out to get the app running.
        pass

    # ── Keyboard shortcuts ──

    def _setup_shortcuts(self) -> None:
        def _open(_: str) -> None:
            self._on_open("")

        def _export(_: str) -> None:
            if self.sf:
                self._on_export_json("")

        def _clear(_: str) -> None:
            self._on_clear("")

        try:
            with dpg.key_handler() as kh:
                dpg.add_key_press_handler(dpg.mvKey_Control | dpg.mvKey_O, callback=_open)
                dpg.add_key_press_handler(dpg.mvKey_Control | dpg.mvKey_E, callback=_export)
                dpg.add_key_press_handler(dpg.mvKey_Escape, callback=_clear)
            dpg.install_key_map_handler(kh)
        except Exception:
            # Keyboard shortcuts not available in this dearpygui version
            pass

    # ── Menu ──

    def _build_menu(self) -> None:
        with dpg.window(tag="menubar", no_title_bar=True, no_resize=True,
                        no_move=True, no_close=True, width=1200, height=30):
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Open Save File…  Ctrl+O",
                                     callback=self._on_open)
                    dpg.add_menu_item(label="Open Recent…",
                                     callback=self._on_recent_list)
                    dpg.add_menu_item(label="Export JSON…  Ctrl+E",
                                     callback=self._on_export_json)
                    dpg.add_menu_item(label="Export CSV…",
                                     callback=self._on_export_csv)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Exit",
                                     callback=lambda _: dpg.exit())

                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Raw XML",
                                     callback=self._show_xml_tab)
                    dpg.add_menu_item(label="Clear",
                                     callback=self._on_clear)

                with dpg.menu(label="Help"):
                    dpg.add_menu_item(label="About",
                                     callback=self._on_about)

    def _on_recent_list(self, _: str) -> None:
        recent = _load_recent()
        if not recent:
            self._set_status("No recent saves.")
            return
        with dpg.window(label="Recent Saves", modal=True, width=400, height=300,
                       pos=(400, 240)) as w:
            with dpg.child_window(width=-10, height=240):
                for rp in recent:
                    btn_path = Path(rp)
                    label = btn_path.name
                    dpg.add_button(
                        label=label,
                        width=-10,
                        callback=self._on_recent,
                        user_data=rp,
                    )
            dpg.add_separator()
            dpg.add_button(label="Close", callback=lambda _: dpg.close_popup(w))
        dpg.bind_popup(w)

    # ── Panels ──

    def _build_panels(self) -> None:
        # ── Sidebar ──
        with dpg.window(tag="sidebar", no_resize=True, no_move=True, no_close=True,
                        width=290, pos=(0, 30), height=750):

            # Drop zone
            with dpg.child_window(tag="drop_zone", width=-10, height=60,
                                  no_scrollbar=True):
                dpg.add_text("Drop .save file here", tag="drop_text")
                # dpg.mvFont_PopupFont is None in some DPG 1.11.x builds
                dpg.set_item_default_color("drop_text", (150, 150, 150))

            dpg.add_button(label="Open File",
                          callback=self._on_open, width=-10)
            dpg.add_button(label="Clear",
                          callback=self._on_clear, width=-10)

            dpg.add_separator()

            # Recent saves title
            with dpg.group(tag="recent_header"):
                dpg.add_text("Recent Saves", tag="recent_title")
                dpg.add_spacer()
                if dpg.does_item_exist("recent_refresh"):
                    dpg.delete_item("recent_refresh")

            with dpg.child_window(tag="recent_files", width=-10, height=160,
                                  no_scrollbar=True):
                pass

            dpg.add_spacer()
            dpg.add_separator()

            # Stats panel
            with dpg.child_window(tag="quick_stats", width=-10, height=180,
                                  no_scrollbar=True):
                dpg.add_text("No file loaded", tag="stats_name")

        # ── Main content ──
        with dpg.window(tag="content", no_resize=True, no_move=True, no_close=True,
                        pos=(295, 30), width=905, height=750):
            with dpg.tab_bar(tag="main_tabs"):
                dpg.add_tab(label="Characters", tag="tab_chars")
                dpg.add_tab(label="Submarine", tag="tab_sub")
                dpg.add_tab(label="Hulls", tag="tab_hulls")
                dpg.add_tab(label="Items", tag="tab_items")
                dpg.add_tab(label="Campaign", tag="tab_campaign")
                dpg.add_tab(label="Missions", tag="tab_missions")
                dpg.add_tab(label="Raw XML", tag="tab_xml")

    def _build_statusbar(self) -> None:
        dpg.add_status_bar(callback=lambda _: None)
        dpg.set_status_bar_item("Ready. Drop a .save file to begin.")

    def _setup_drop_target(self) -> None:
        try:
            # Register drop callback on the viewport
            dpg.set_drag_and_drop_callback(self._on_drop_viewport)
        except Exception:
            # Drag-and-drop not available in this DPG version
            pass

    # ── Drop target ──

    def _on_drop_viewport(self, data: dict) -> None:
        paths = data.get("paths", [])
        if paths:
            self._on_file_selected("", paths[0])

    # ── Actions ──

    def _on_open(self, _: str) -> None:
        # Use native Windows file dialog
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        root.attributes("-topmost", True)  # Bring dialog to front
        filepath = filedialog.askopenfilename(
            title="Open Barotrauma Save File",
            filetypes=[("Save files", "*.save"), ("All files", "*.*")],
            initialdir=str(
                Path.home() / "AppData" / "LocalLow"
                / "Eyefish" / "Barotrauma" / "saves"
            ),
        )
        root.destroy()
        
        if filepath:
            self._on_file_selected("", filepath)

    def _on_file_selected(self, _: str, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            return

        self.file_path = path
        self.char_filter = "All"
        self.item_filter = "All"
        self.char_search = ""
        self.item_search = ""

        # Save to recent
        recent = _load_recent()
        fp = str(path.resolve())
        if fp not in recent:
            recent.insert(0, fp)
            if len(recent) > 10:
                recent = recent[:10]
            _save_recent(recent)

        # Refresh recent list buttons
        self._render_recent_buttons(recent)

        try:
            self.sf = parse_save(path)
            self._update_all()
            self._set_status(
                f"Loaded: {path.name} | {len(self.sf.characters)} chars "
                f"| {len(self.sf.hulls)} hulls | {len(self.sf.items)} items | "
                f"{len(self.sf.missions)} missions"
            )
        except Exception as e:
            self._set_status(f"Error: {e}")
            self.sf = None

    def _render_recent_buttons(self, recent: list[str]) -> None:
        if not dpg.does_item_exist("recent_files"):
            return
        # Remove old buttons (children only)
        for item in dpg.get_item_children("recent_files", 1):
            dpg.delete_item(item, children_only=True)
        for rp in recent:
            label = Path(rp).name
            dpg.add_button(
                label=label,
                width=-5,
                callback=self._on_recent,
                user_data=rp,
            )

    def _refresh_recent_files(self) -> None:
        """Refresh the recent files list in the sidebar."""
        recent = _load_recent()
        if not recent:
            return
        
        # Remove old recent files section if exists
        if dpg.does_item_exist("recent_header"):
            dpg.delete_item("recent_header")
        if dpg.does_item_exist("recent_files"):
            dpg.delete_item("recent_files")
        
        # Rebuild recent files section
        with dpg.group(tag="recent_header", parent="sidebar"):
            dpg.add_text("Recent Saves", tag="recent_title")
            dpg.add_spacer()
        
        with dpg.child_window(tag="recent_files", width=-10, height=160,
                              no_scrollbar=True, parent="sidebar"):
            for rp in recent:
                btn_path = Path(rp)
                label = btn_path.name
                dpg.add_button(
                    label=label,
                    width=-5,
                    callback=self._on_recent,
                    user_data=rp,
                )

    def _on_recent(self, _: str, user_data: str) -> None:
        self._on_file_selected("", user_data)

    def _on_clear(self, _: str) -> None:
        self.sf = None
        self.file_path = None
        self.char_filter = "All"
        self.item_filter = "All"
        self.char_search = ""
        self.item_search = ""
        self._update_all()
        self._set_status("Ready. Drop a .save file to begin.")

    def _on_export_json(self, _: str) -> None:
        if not self.sf:
            return
        
        # Use native Windows file dialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.asksaveasfilename(
            title="Export to JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(self.file_path.parent) if self.file_path else None,
            initialfile=f"{self.file_path.stem}.json" if self.file_path else None,
        )
        root.destroy()
        
        if filepath:
            self._write_json(filepath)

    def _on_export_csv(self, _: str) -> None:
        if not self.sf:
            return
        
        # Use native Windows file dialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filepath = filedialog.asksaveasfilename(
            title="Export Characters to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=str(self.file_path.parent) if self.file_path else None,
            initialfile=f"{self.file_path.stem}-chars.csv" if self.file_path else None,
        )
        root.destroy()
        
        if filepath:
            self._write_csv(filepath)

    def _on_export_csv(self, _: str) -> None:
        if not self.sf:
            return
        
        dpg.show_file_dialog(
            file_count=1,
            modal=False,
            callback=lambda _, f: self._write_csv(f),
            default_path=(
                str(self.file_path.parent / f"{self.file_path.stem}-chars.csv")
                if self.file_path else None
            ),
        )

    def _write_json(self, filepath: str) -> None:
        if not self.sf:
            return
        data = {
            "filename": str(self.sf.path),
            "submarine": vars(self.sf.submarine),
            "characters": [vars(c) for c in self.sf.characters],
            "hulls": [vars(h) for h in self.sf.hulls],
            "structures": [vars(s) for s in self.sf.structures],
            "items": [vars(i) for i in self.sf.items],
            "locations": [vars(l) for l in self.sf.locations],
            "missions": [vars(m) for m in self.sf.missions],
        }
        Path(filepath).write_text(json.dumps(data, indent=2, default=str))
        self._set_status(f"Exported JSON: {Path(filepath).name}")

    def _write_csv(self, filepath: str) -> None:
        if not self.sf:
            return
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Name", "Job", "Condition", "Status",
                         "Dead", "Position", "DestinationIdx", "Tags"])
        for c in self.sf.characters:
            writer.writerow([
                c.id, c.name, c.job, c.condition, c.status,
                str(c.permanently_dead), c.position,
                str(c.destination_index) if c.destination_index is not None else "",
                c.tags,
            ])
        Path(filepath).write_text(buf.getvalue())
        self._set_status(f"Exported CSV: {Path(filepath).name}")

    def _on_about(self, _: str) -> None:
        with dpg.window(label="About", modal=True, width=400, height=220,
                       pos=(400, 260)) as w:
            dpg.add_text("Barotrauma Save Viewer")
            dpg.add_text("Parses .save files and displays structured data.")
            dpg.add_text("Characters, hulls, items, missions, and campaign data.")
            dpg.add_text("Ctrl+O Open | Ctrl+E Export JSON | Esc Clear")
            dpg.add_button(label="OK", callback=lambda _: dpg.close_popup(w))
        dpg.bind_popup(w)

    def _show_xml_tab(self, _: str) -> None:
        dpg.set_value("main_tabs", "tab_xml")

    # ── Updates ──

    def _update_all(self) -> None:
        if not self.sf:
            self._update_empty()
            return
        self._update_stats()
        self._refresh_tables()

    def _update_empty(self) -> None:
        dpg.configure_item("stats_name", default_value="No file loaded")
        for tag in ("chars_table", "sub_text", "hulls_table", "items_table"):
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, default_value="No data available.")
        for tag in ("campaign_text", "missions_text", "xml_text"):
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, default_value="No data available.")

    def _update_stats(self) -> None:
        sf = self.sf
        if not sf:
            return

        name = sf.submarine.name or "Unknown"
        hp = (f"{sf.submarine.sub_type}/{sf.submarine.class_}"
              if sf.submarine.sub_type != "Unknown" else "")
        tier = (f"tier {sf.submarine.tier}"
                if sf.submarine.tier != "Unknown" else "")
        size = f"{sf.original_size:,}B / {sf.decompressed_size:,}B"

        alive = len([c for c in sf.characters if not c.permanently_dead])
        dead = len([c for c in sf.characters if c.permanently_dead])

        stats = (f"  🚢 {name}\n"
                 f"     {hp} | {tier}\n"
                 f"  📏 {size}\n"
                 f"  👥 {len(sf.characters)}  ({alive} alive, {dead} dead)\n"
                 f"  🛡 {len(sf.hulls)} hulls | {len(sf.structures)} structures\n"
                 f"  📦 {len(sf.items)} items\n"
                 f"  📍 {len(sf.locations)} locations\n"
                 f"  📋 {len(sf.missions)} missions")
        dpg.configure_item("stats_name", default_value=stats)

    def _refresh_tables(self) -> None:
        if not self.sf:
            return
        self._refresh_chars_table()
        self._refresh_sub_table()
        self._refresh_hulls_table()
        self._refresh_items_table()
        self._refresh_campaign_text()
        self._refresh_missions_table()
        self._refresh_xml_text()

    def _clear_table_rows(self, table_tag: str) -> None:
        if not dpg.does_item_exist(table_tag):
            return
        for item in dpg.get_item_children(table_tag, 1):
            dpg.delete_item(item, children_only=True)

    # ── Characters Tab ──

    def _refresh_chars_table(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_chars"):
            return

        # Remove old controls if exists
        for tag in ("chars_table", "chars_filter", "chars_search"):
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

        # Toolbar row
        with dpg.group(tag="chars_toolbar", horizontal=True):
            job_types = sorted({"All", *{c.job for c in self.sf.characters}})
            dpg.add_combo(job_types, default_value=self.char_filter,
                          width=140, callback=self._filter_chars,
                          tag="chars_filter")
            dpg.add_input_text(default_value=self.char_search, width=200,
                              callback=self._filter_chars_search,
                              placeholder="Search names…", tag="chars_search")
            dpg.add_text(f"  {len(self.sf.characters)} total")

        dpg.reparent_item("chars_toolbar", "tab_chars")

        table = dpg.add_table(
            tag="chars_table",
            columns=[
                dpg.add_table_column(label="ID", width=50),
                dpg.add_table_column(label="Name", width=180),
                dpg.add_table_column(label="Job", width=130),
                dpg.add_table_column(label="HP", width=80),
                dpg.add_table_column(label="Status", width=100),
            ],
        )
        dpg.reparent_item(table, "tab_chars")

        self._populate_chars_table(self.char_filter, self.char_search)

    def _filter_chars(self, _: str, value: str) -> None:
        self.char_filter = value
        self._refresh_chars_table()

    def _filter_chars_search(self, _: str, value: str) -> None:
        self.char_search = value
        if self.sf:
            self._populate_chars_table(self.char_filter, self.char_search)

    def _populate_chars_table(self, job_filter: str, search: str = "") -> None:
        if not self.sf or not dpg.does_item_exist("chars_table"):
            return

        filtered = [c for c in self.sf.characters
                     if (job_filter == "All" or c.job == job_filter)
                     and (not search or search.lower() in c.name.lower())]
        self._clear_table_rows("chars_table")

        for c in filtered:
            row = dpg.add_table_row("chars_table")
            dpg.add_text(c.id, parent=row)
            txt_name = dpg.add_text(c.name, parent=row)
            col = _status_color(c)
            dpg.configure_item(txt_name, default_color=col)
            dpg.add_text(c.job, parent=row)

            # Health with color
            txt_hp = dpg.add_text(c.condition, parent=row)
            try:
                hp_val = float(c.condition.rstrip("%"))
                dpg.configure_item(txt_hp, default_color=_condition_color(hp_val))
            except ValueError:
                pass

            txt_status = dpg.add_text(_status_label(c), parent=row)
            dpg.configure_item(txt_status, default_color=_status_color(c))

    # ── Submarine Tab ──

    def _refresh_sub_table(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_sub"):
            return
        sf = self.sf
        lines = [
            (f"  🚢 Name",    sf.submarine.name or "Unknown"),
            (f"  🔷 Type",    sf.submarine.sub_type or "Unknown"),
            (f"  🏷 Class",   sf.submarine.class_ or "Unknown"),
            (f"  ⭐ Tier",    sf.submarine.tier or "Unknown"),
            (f"  🎮 GameVer", sf.submarine.game_version or "Unknown"),
            (f"  📏 Dimensions", sf.submarine.dimensions or "Unknown"),
            (f"  📦 Cargo Cap", sf.submarine.cargo_capacity or "Unknown"),
            (f"  💰 Price",   sf.submarine.price or "Unknown"),
            (f"  🏷 Tags",    sf.submarine.tags or "Unknown"),
        ]
        text = "\n".join(f"{k:<16} {v}" for k, v in lines)

        if not dpg.does_item_exist("sub_text"):
            dpg.add_text(text, tag="sub_text")
            dpg.reparent_item("sub_text", "tab_sub")
        else:
            dpg.configure_item("sub_text", default_value=text)

    # ── Hulls Tab ──

    def _refresh_hulls_table(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_hulls"):
            return

        if dpg.does_item_exist("hulls_table"):
            dpg.delete_item("hulls_table")

        table = dpg.add_table(
            tag="hulls_table",
            columns=[
                dpg.add_table_column(label="ID", width=60),
                dpg.add_table_column(label="Name", width=140),
                dpg.add_table_column(label="Health", width=120),
                dpg.add_table_column(label="Integrity", width=90),
                dpg.add_table_column(label="Damage", width=70),
            ],
        )
        dpg.reparent_item(table, "tab_hulls")

        for h in self.sf.hulls:
            row = dpg.add_table_row("hulls_table")
            dpg.add_text(h.id, parent=row)
            dpg.add_text(h.name, parent=row)

            # Health with emoji + value
            hp_label = f"{_health_bar(h)} {h.health_pct:.1f}%"
            hp_col = _condition_color(h.health_pct)
            txt_hp = dpg.add_text(hp_label, parent=row)
            dpg.configure_item(txt_hp, default_color=hp_col)

            int_col = _condition_color(h.integrity)
            txt_int = dpg.add_text(f"{h.integrity:.1f}", parent=row)
            dpg.configure_item(txt_int, default_color=int_col)

            dmg_col = _condition_color(100 - h.damage) if h.damage > 0 else (200, 200, 200)
            dpg.add_text(f"{h.damage:.1f}", parent=row, default_color=dmg_col)

    # ── Items Tab ──

    def _refresh_items_table(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_items"):
            return

        for tag in ("items_table", "items_filter", "items_search"):
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

        # Toolbar
        with dpg.group(tag="items_toolbar", horizontal=True):
            item_types = sorted({"All", *{i.item_type for i in self.sf.items}})
            dpg.add_combo(item_types, default_value=self.item_filter,
                          width=130, callback=self._filter_items,
                          tag="items_filter")
            dpg.add_input_text(default_value=self.item_search, width=200,
                              callback=self._filter_items_search,
                              placeholder="Search items…", tag="items_search")
            dpg.add_text(f"  {len(self.sf.items)} total")

        dpg.reparent_item("items_toolbar", "tab_items")

        table = dpg.add_table(
            tag="items_table",
            columns=[
                dpg.add_table_column(label="ID", width=60),
                dpg.add_table_column(label="Identifier", width=180),
                dpg.add_table_column(label="Type", width=80),
                dpg.add_table_column(label="Condition", width=140),
                dpg.add_table_column(label="Position", width=220),
            ],
        )
        dpg.reparent_item(table, "tab_items")

        self._populate_items_table(self.item_filter, self.item_search)

    def _filter_items(self, _: str, value: str) -> None:
        self.item_filter = value
        self._refresh_items_table()

    def _filter_items_search(self, _: str, value: str) -> None:
        self.item_search = value
        if self.sf:
            self._populate_items_table(self.item_filter, self.item_search)

    def _populate_items_table(self, type_filter: str, search: str = "") -> None:
        if not self.sf or not dpg.does_item_exist("items_table"):
            return

        filtered = [i for i in self.sf.items
                     if (type_filter == "All" or i.item_type == type_filter)
                     and (not search or search.lower() in i.identifier.lower())]
        self._clear_table_rows("items_table")

        for i in filtered:
            row = dpg.add_table_row("items_table")
            dpg.add_text(i.id, parent=row)
            txt_id = dpg.add_text(i.identifier, parent=row)
            dpg.configure_item(txt_id, default_color=(180, 190, 220))
            dpg.add_text(i.item_type, parent=row)

            # Condition with bar
            bar = _item_bar_pct(i.condition_pct)
            col = _condition_color(i.condition_pct)
            cond_txt = f"{i.condition_pct:.0f}% {bar}"
            txt_cond = dpg.add_text(cond_txt, parent=row)
            dpg.configure_item(txt_cond, default_color=col)

            dpg.add_text(i.position, parent=row)

    # ── Campaign Tab ──

    def _refresh_campaign_text(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_campaign"):
            return

        lines = []
        if self.sf.campaign_settings:
            cs = self.sf.campaign_settings
            lines.append(f"  Max Missions:    {cs.max_mission_count or 'N/A'}")
            lines.append(f"  Max Attempts:    {cs.max_mission_attempts or 'N/A'}")
            for k, v in cs.extra.items():
                lines.append(f"  {k}:             {v}")

        if self.sf.locations:
            lines.append("\n  Locations:")
            for loc in self.sf.locations:
                lines.append(f"    {loc.index or '?':>3}.  {loc.name:<30s} ({loc.location_type}, {loc.biome})")

        if not lines:
            text = "No campaign data available."
        else:
            text = "\n".join(lines)

        if not dpg.does_item_exist("campaign_text"):
            dpg.add_text(text, tag="campaign_text")
            dpg.reparent_item("campaign_text", "tab_campaign")
        else:
            dpg.configure_item("campaign_text", default_value=text)

    # ── Missions Tab ──

    def _refresh_missions_table(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_missions"):
            return

        if dpg.does_item_exist("missions_table"):
            dpg.delete_item("missions_table")

        if not self.sf.missions:
            txt = dpg.add_text("No missions found.", tag="missions_table")
            dpg.reparent_item("missions_table", "tab_missions")
            return

        table = dpg.add_table(
            tag="missions_table",
            columns=[
                dpg.add_table_column(label="Selected", width=60),
                dpg.add_table_column(label="Prefab ID", width=180),
                dpg.add_table_column(label="Destination", width=160),
                dpg.add_table_column(label="Type", width=100),
                dpg.add_table_column(label="Attempts", width=70),
                dpg.add_table_column(label="Status", width=90),
            ],
        )
        dpg.reparent_item(table, "tab_missions")

        for m in self.sf.missions:
            row = dpg.add_table_row("missions_table")
            sel_icon = "✓" if m.selected else "—"
            col_sel = (80, 220, 80) if m.selected else (100, 100, 100)
            txt_sel = dpg.add_text(sel_icon, parent=row)
            dpg.configure_item(txt_sel, default_color=col_sel)

            txt_id = dpg.add_text(m.prefab_id, parent=row)
            dpg.configure_item(txt_id, default_color=(180, 190, 220))

            dpg.add_text(m.location, parent=row)
            dpg.add_text(m.mission_type, parent=row)
            dpg.add_text(str(m.times_attempted), parent=row)

            # Status
            if m.times_attempted == 0:
                status = "Not attempted"
                col_st = (150, 150, 150)
            elif m.selected:
                status = "Active"
                col_st = (80, 200, 80)
            else:
                status = "Failed"
                col_st = (220, 80, 80)
            txt_st = dpg.add_text(status, parent=row)
            dpg.configure_item(txt_st, default_color=col_st)

    # ── Raw XML Tab ──

    def _refresh_xml_text(self) -> None:
        if not self.sf or not dpg.does_item_exist("tab_xml"):
            return

        xml_preview = ""
        if self.sf.raw_xml:
            xml_preview = self.sf.raw_xml[:10000]
            if len(self.sf.raw_xml) > 10000:
                xml_preview += "\n\n...(truncated, total size: " + f"{len(self.sf.raw_xml):,}" + " chars)"
        else:
            xml_preview = "No raw XML available."

        if not dpg.does_item_exist("xml_text"):
            dpg.add_text(xml_preview, tag="xml_text")
            dpg.reparent_item("xml_text", "tab_xml")
        else:
            dpg.configure_item("xml_text", default_value=xml_preview)

    # ── Helpers ──

    def _set_status(self, text: str) -> None:
        dpg.set_status_bar_item(text)


def main() -> None:
    try:
        app = SaveViewer()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
