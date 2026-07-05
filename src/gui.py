#!/usr/bin/env python3
"""PySide6 GUI for Barotrauma save file viewer."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QFileDialog, QMessageBox, QTextEdit, QComboBox,
    QLineEdit, QHeaderView, QTabWidget,
    QGroupBox, QMenu, QDialog, QScrollArea,
    QFrame, QAbstractItemView, QGraphicsView, QGraphicsScene,
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import (
    QKeySequence, QAction, QColor, QFont, QPen, QBrush,
    QPolygonF, QWheelEvent, QPainter,
)

try:
    from parser.data import SaveFile, Character, Item, Hull, Mission, Location
    from parser.decode import parse_save
except ImportError:
    from data import SaveFile, Character, Item, Hull, Mission, Location
    from decode import parse_save


# ─── Color helpers ────────────────────────────────────────────────

def _condition_color(pct: float) -> QColor:
    if pct >= 70:
        return QColor(80, 220, 80)
    if pct >= 40:
        return QColor(240, 200, 60)
    if pct >= 15:
        return QColor(240, 140, 50)
    return QColor(230, 60, 60)


def _status_color(char: Character) -> QColor:
    if char.permanently_dead or char.status == "Dead":
        return QColor(180, 50, 50)
    cond_val = 100.0
    if char.condition.endswith("%"):
        try:
            cond_val = float(char.condition.rstrip("%"))
        except ValueError:
            pass
    return _condition_color(cond_val)


def _status_label(char: Character) -> str:
    if char.permanently_dead or char.status == "Dead":
        return "Dead"
    if char.status == "Campaign":
        return "Campaign"
    if char.status == "In Duffelbag":
        return "Duffelbag"
    return char.status


def _health_bar_text(h: Hull) -> str:
    if h.health_pct >= 80:
        return "\u25a1\u25a1\u25a1\u25a1\u25a1\u25a1\u25a1\u25a1\u25a1\u25a1"
    if h.health_pct >= 40:
        return "\u25a1\u25a1\u25a1\u25a1\u25a1\u2591\u2591\u2591\u2591\u2591"
    if h.health_pct >= 20:
        return "\u25a1\u25a1\u25a1\u2591\u2591\u2591\u2591\u2591\u2591\u2591"
    return "\u25a1\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591"


def _item_bar_text(pct: float) -> str:
    if pct >= 80:
        return "\u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2593"
    if pct >= 50:
        return "\u2593\u2593\u2593\u2593\u2593\u2591\u2591\u2591\u2591\u2591"
    if pct >= 20:
        return "\u2593\u2593\u2593\u2591\u2591\u2591\u2591\u2591\u2591\u2591"
    return "\u2593\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591"


# ─── Biome colors ────────────────────────────────────────────────

BIOME_PALETTE: dict[str, QColor] = {
    "Deep Ocean":    QColor(0x00, 0x3d, 0x7a),
    "Ocean":         QColor(0x00, 0x77, 0xb6),
    "Shallow":       QColor(0x33, 0xcc, 0xff),
    "Caves":         QColor(0x99, 0x66, 0x33),
    "Ice Caves":     QColor(0xcc, 0xff, 0xff),
    "Lava Caves":    QColor(0xff, 0x66, 0x00),
    "Mushroom":      QColor(0xcc, 0x99, 0xcc),
    "Mushroom Caves": QColor(0xcc, 0x99, 0xcc),
    "Molten Sea":    QColor(0xff, 0x33, 0x00),
    "Deep Sea":      QColor(0x00, 0x33, 0x66),
    "Surface":       QColor(0x00, 0xcc, 0x66),
}
DEFAULT_BIOME_COLOR = QColor(0x66, 0x99, 0xcc)


def _biome_color(biome: str) -> QColor:
    for key, col in BIOME_PALETTE.items():
        if key.lower() in biome.lower():
            return col
    return DEFAULT_BIOME_COLOR


# ─── Recent saves ────────────────────────────────────────────────

def _recent_path() -> Path:
    return Path.home() / ".reverse-baro" / "recent.json"


def _load_recent() -> list[str]:
    p = _recent_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _save_recent(paths: list[str]) -> None:
    seen: list[str] = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    p = _recent_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(seen[:10], indent=2))


# ─── Separator factory ───────────────────────────────────────────

def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFrameShadow(QFrame.Sunken)
    f.setStyleSheet("color: #444;")
    return f


# ─── Sidebar Widget ──────────────────────────────────────────────

class Sidebar(QWidget):
    open_signal = Signal()
    clear_signal = Signal()
    recent_click = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(6)

        self.drop_label = QLabel("Drop .save file here")
        self.drop_label.setStyleSheet(
            "color: #999; font-size: 11pt; padding: 15px; "
            "border: 2px dashed #444; border-radius: 6px;"
        )
        self.layout.addWidget(self.drop_label)

        self.open_btn = QPushButton("Open File")
        self.open_btn.clicked.connect(self.open_signal.emit)
        self.layout.addWidget(self.open_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_signal.emit)
        self.layout.addWidget(self.clear_btn)

        self.layout.addSpacing(6)
        self.layout.addWidget(_sep())

        recent_title = QLabel("Recent Saves")
        recent_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.layout.addWidget(recent_title)

        self.recent_area = QScrollArea()
        self.recent_area.setWidgetResizable(True)
        self.recent_area.setMaximumHeight(160)
        self.recent_widget = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_widget)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(2)
        self.recent_area.setWidget(self.recent_widget)
        self.layout.addWidget(self.recent_area)

        self.layout.addStretch()
        self.layout.addWidget(_sep())

        self.stats_frame = QGroupBox("Quick Stats")
        self.stats_layout = QVBoxLayout(self.stats_frame)
        self.stats_label = QLabel("No file loaded")
        self.stats_label.setWordWrap(True)
        self.stats_layout.addWidget(self.stats_label)
        self.layout.addWidget(self.stats_frame)

    def update_recent(self, recent: list[str]):
        while self.recent_layout.count():
            child = self.recent_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for rp in recent:
            btn = QPushButton(Path(rp).name)
            btn.setMaximumHeight(28)
            btn.setToolTip(rp)
            btn.clicked.connect(lambda _, p=rp: self.recent_click.emit(p))
            self.recent_layout.addWidget(btn)

    def update_stats(self, text: str):
        self.stats_label.setText(text)


# ─── Characters Widget ───────────────────────────────────────────

class CharactersWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(140)
        self.filter_combo.currentTextChanged.connect(self._on_filter)
        toolbar.addWidget(QLabel("Filter:"))
        toolbar.addWidget(self.filter_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search names...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(QLabel("Search:"))
        toolbar.addWidget(self.search_input)

        self.total_label = QLabel("")
        toolbar.addWidget(self.total_label)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Job", "HP", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layout.addWidget(self.table)

        self._characters: list[Character] = []

    def set_data(self, characters: list[Character]):
        self._characters = characters
        job_types = sorted({"All", *{c.job for c in characters}})
        self.filter_combo.clear()
        self.filter_combo.addItems(job_types)
        self.filter_combo.setCurrentText("All")
        self._populate()

    def _on_filter(self):
        self._populate()

    def _on_search(self):
        self._populate()

    def _populate(self):
        job_filter = self.filter_combo.currentText()
        search = self.search_input.text().lower()

        filtered = [
            c for c in self._characters
            if (job_filter == "All" or c.job == job_filter)
            and (not search or search in c.name.lower())
        ]
        self.total_label.setText(f"{len(filtered)} / {len(self._characters)} total")

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(c.id))
            name_item = QTableWidgetItem(c.name)
            name_item.setForeground(_status_color(c))
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(c.job))
            cond_item = QTableWidgetItem(c.condition)
            try:
                hp_val = float(c.condition.rstrip("%"))
                cond_item.setForeground(_condition_color(hp_val))
            except ValueError:
                pass
            self.table.setItem(row, 3, cond_item)
            status_item = QTableWidgetItem(_status_label(c))
            status_item.setForeground(_status_color(c))
            self.table.setItem(row, 4, status_item)


# ─── Submarine Widget ────────────────────────────────────────────

class SubmarineWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

    def set_data(self, submarine, original_size: int, decompressed_size: int):
        lines = [
            (f"\U0001f682 Name", submarine.name or "Unknown"),
            (f"\U0001f537 Type", submarine.sub_type or "Unknown"),
            (f"\U0001f3f7\ufe0f Class", submarine.class_ or "Unknown"),
            (f"\u2b50 Tier", submarine.tier or "Unknown"),
            (f"\U0001f3ae GameVer", submarine.game_version or "Unknown"),
            (f"\U0001f4cf Dimensions", submarine.dimensions or "Unknown"),
            (f"\U0001f4e6 Cargo Cap", submarine.cargo_capacity or "Unknown"),
            (f"\U0001f4b0 Price", submarine.price or "Unknown"),
            (f"\U0001f3f7\ufe0f Tags", submarine.tags or "Unknown"),
        ]
        text = "\n".join(f"{k:<16} {v}" for k, v in lines)
        text += f"\n\nOriginal size:   {original_size:,} bytes"
        text += f"\nDecompressed:    {decompressed_size:,} bytes"
        self.text_edit.setPlainText(text)


# ─── Hulls Widget ────────────────────────────────────────────────

class HullsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Health", "Integrity", "Damage"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 70)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layout.addWidget(self.table)

    def set_data(self, hulls: list[Hull]):
        self.table.setRowCount(len(hulls))
        for row, h in enumerate(hulls):
            self.table.setItem(row, 0, QTableWidgetItem(h.id))
            self.table.setItem(row, 1, QTableWidgetItem(h.name))
            hp_item = QTableWidgetItem(f"{h.health_pct:.1f}%")
            hp_item.setForeground(_condition_color(h.health_pct))
            self.table.setItem(row, 2, hp_item)
            int_item = QTableWidgetItem(f"{h.integrity:.1f}")
            int_item.setForeground(_condition_color(h.integrity))
            self.table.setItem(row, 3, int_item)
            dmg_item = QTableWidgetItem(f"{h.damage:.1f}")
            if h.damage > 0:
                dmg_item.setForeground(_condition_color(100 - h.damage))
            self.table.setItem(row, 4, dmg_item)


# ─── Items Widget ────────────────────────────────────────────────

class ItemsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(130)
        self.filter_combo.currentTextChanged.connect(self._on_filter)
        toolbar.addWidget(QLabel("Filter:"))
        toolbar.addWidget(self.filter_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(QLabel("Search:"))
        toolbar.addWidget(self.search_input)

        self.total_label = QLabel("")
        toolbar.addWidget(self.total_label)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Identifier", "Type", "Condition", "Position"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 220)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layout.addWidget(self.table)

        self._items: list[Item] = []

    def set_data(self, items: list[Item]):
        self._items = items
        item_types = sorted({"All", *{i.item_type for i in items}})
        self.filter_combo.clear()
        self.filter_combo.addItems(item_types)
        self.filter_combo.setCurrentText("All")
        self._populate()

    def _on_filter(self):
        self._populate()

    def _on_search(self):
        self._populate()

    def _populate(self):
        type_filter = self.filter_combo.currentText()
        search = self.search_input.text().lower()

        filtered = [
            i for i in self._items
            if (type_filter == "All" or i.item_type == type_filter)
            and (not search or search in i.identifier.lower())
        ]
        self.total_label.setText(f"{len(filtered)} / {len(self._items)} total")

        self.table.setRowCount(len(filtered))
        for row, i in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(i.id))
            id_item = QTableWidgetItem(i.identifier)
            id_item.setForeground(QColor(180, 190, 220))
            self.table.setItem(row, 1, id_item)
            self.table.setItem(row, 2, QTableWidgetItem(i.item_type))
            bar = _item_bar_text(i.condition_pct)
            cond_item = QTableWidgetItem(f"{i.condition_pct:.0f}% {bar}")
            cond_item.setForeground(_condition_color(i.condition_pct))
            self.table.setItem(row, 3, cond_item)
            self.table.setItem(row, 4, QTableWidgetItem(i.position))


# ─── Campaign Widget ─────────────────────────────────────────────

class CampaignWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

    def set_data(self, sf: SaveFile):
        lines = []
        if sf.campaign_settings:
            cs = sf.campaign_settings
            lines.append(f"Max Missions:    {cs.max_mission_count or 'N/A'}")
            lines.append(f"Max Attempts:    {cs.max_mission_attempts or 'N/A'}")
            for k, v in cs.extra.items():
                lines.append(f"{k}:             {v}")
        if sf.locations:
            lines.append("\nLocations:")
            for loc in sf.locations:
                idx = loc.index if loc.index is not None else "?"
                lines.append(
                    f"  {idx:>3}.  {loc.name:<30s} ({loc.location_type}, {loc.biome})"
                )
        self.text_edit.setPlainText(
            "\n".join(lines) if lines else "No campaign data available."
        )


# ─── Missions Widget ─────────────────────────────────────────────

class MissionsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Selected", "Prefab ID", "Destination", "Type", "Attempts", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 90)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layout.addWidget(self.table)

    def set_data(self, missions: list[Mission]):
        self.table.setRowCount(len(missions))
        for row, m in enumerate(missions):
            sel_item = QTableWidgetItem("\u2713" if m.selected else "\u2014")
            sel_item.setForeground(
                QColor(80, 220, 80) if m.selected else QColor(100, 100, 100)
            )
            self.table.setItem(row, 0, sel_item)

            id_item = QTableWidgetItem(m.prefab_id)
            id_item.setForeground(QColor(180, 190, 220))
            self.table.setItem(row, 1, id_item)

            self.table.setItem(row, 2, QTableWidgetItem(m.location))
            self.table.setItem(row, 3, QTableWidgetItem(m.mission_type))
            self.table.setItem(row, 4, QTableWidgetItem(str(m.times_attempted)))

            if m.times_attempted == 0:
                status, col_st = "Not attempted", QColor(150, 150, 150)
            elif m.selected:
                status, col_st = "Active", QColor(80, 200, 80)
            else:
                status, col_st = "Failed", QColor(220, 80, 80)
            status_item = QTableWidgetItem(status)
            status_item.setForeground(col_st)
            self.table.setItem(row, 5, status_item)


# ─── Raw XML Widget ──────────────────────────────────────────────

class RawXmlWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.text_edit.setFont(font)
        self.layout.addWidget(self.text_edit)

    def set_data(self, raw_xml: str | None):
        if raw_xml:
            preview = raw_xml[:10000]
            if len(raw_xml) > 10000:
                preview += f"\n\n...(truncated, total size: {len(raw_xml):,} chars)"
        else:
            preview = "No raw XML available."
        self.text_edit.setPlainText(preview)


# ─── Map Widget ──

class MapWidget(QWidget):
    """Interactive map of Barotrauma locations."""

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar: zoom controls + legend
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 4)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setMaximumWidth(32)
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar.addWidget(self._zoom_in_btn)

        self._zoom_out_btn = QPushButton("-")
        self._zoom_out_btn.setMaximumWidth(32)
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar.addWidget(self._zoom_out_btn)

        self._fit_btn = QPushButton("Fit")
        self._fit_btn.setMaximumWidth(50)
        self._fit_btn.clicked.connect(self._fit_all)
        toolbar.addWidget(self._fit_btn)

        toolbar.addStretch()

        # Legend
        self._legend_label = QLabel("Legend:")
        toolbar.addWidget(self._legend_label)
        toolbar.addSpacing(6)

        self._legend = QHBoxLayout()
        self._legend.setContentsMargins(0, 0, 0, 0)
        self._legend.setSpacing(4)
        toolbar.addLayout(self._legend)

        self.layout.addLayout(toolbar)

        # Map view
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints() | QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setStyleSheet("""
            QGraphicsView {
                background: #0a0e17;
                border: 1px solid #45475a;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #1e1e2e;
                border: none;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #45475a;
                border-radius: 3px;
                min-height: 20px;
                min-width: 20px;
            }
        """)
        self.layout.addWidget(self.view)

        self._items: list[tuple[float, float, str, str, str]] = []

    def set_data(self, locations: list[Location], submarine_pos: tuple[float, float] | None = None):
        self.scene.clear()
        self._items = []
        self._biome_legend: dict[str, QColor] = {}

        # Draw dark ocean background
        bg = self.scene.addRect(-50000, -50000, 100000, 100000)
        bg.setPen(QPen(Qt.NoPen))
        bg.setBrush(QBrush(QColor("#060d1a")))

        # Grid lines every 500 units
        grid_pen = QPen(QColor("#ffffff08"))
        for i in range(-50000, 50001, 500):
            self.scene.addLine(i, -50000, i, 50000, grid_pen)
            self.scene.addLine(-50000, i, 50000, i, grid_pen)

        # Axes
        axis_pen = QPen(QColor("#ffffff18"))
        self.scene.addLine(-50000, 0, 50000, 0, axis_pen)
        self.scene.addLine(0, -50000, 0, 50000, axis_pen)

        # Parse and plot locations
        for loc in locations:
            if not loc.position or loc.position == "Unknown":
                continue
            coords = self._parse_pos(loc.position)
            if coords is None:
                continue
            x, y = coords
            self._items.append((x, y, loc.name, loc.biome, loc.location_type))

            col = _biome_color(loc.biome)
            self._biome_legend[loc.biome] = col

            # Glow ring
            glow = self.scene.addEllipse(x - 14, y - 14, 28, 28)
            glow.setPen(QPen(col, 1.5))
            glow.setBrush(QBrush(QColor(0, 0, 0, 0)))

            # Dot
            dot = self.scene.addEllipse(x - 8, y - 8, 16, 16)
            dot.setPen(Qt.NoPen)
            dot.setBrush(QBrush(col))

            # Hover target (transparent larger area)
            hover = self.scene.addEllipse(x - 20, y - 20, 40, 40)
            hover.setPen(Qt.NoPen)
            hover.setBrush(Qt.NoBrush)
            hover.setToolTip(
                f"{loc.name}\nType: {loc.location_type}\nBiome: {loc.biome}\nPos: {loc.position}"
            )
            hover.setAcceptHoverEvents(True)

            # Label
            label = self.scene.addText(loc.name)
            label.setDefaultTextColor(QColor("#cdd6f4cc"))
            label.setFont(QFont("Segoe UI", 7))
            label.setPos(x + 14, y - 6)

        # Submarine marker
        if submarine_pos:
            sx, sy = submarine_pos
            sub_shape = QPolygonF([
                (sx, sy - 20), (sx - 14, sy + 10),
                (sx, sy + 4), (sx + 14, sy + 10),
            ])
            sub_item = self.scene.addPolygon(sub_shape)
            sub_item.setBrush(QBrush(QColor(233, 69, 96)))
            sub_item.setPen(QPen(QColor(255, 255, 255, 100), 1))
            sub_item.setToolTip("Submarine")
            sub_item.setAcceptHoverEvents(True)

            sub_label = self.scene.addText("[SUB]")
            sub_label.setDefaultTextColor(QColor(233, 69, 96))
            sub_label.setFont(QFont("Segoe UI", 7, QFont.Bold))
            sub_label.setPos(sx - 12, sy + 16)

        # Build legend
        self._build_legend()

        # Fit view to all points
        if self._items:
            self._fit_all()
        else:
            self.scene.setSceneRect(-1000, -1000, 2000, 2000)

    def _parse_pos(self, pos: str) -> tuple[float, float] | None:
        """Parse 'x,y' or 'x, y' into float tuple."""
        try:
            parts = pos.replace(" ", "").split(",")
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
        except (ValueError, AttributeError):
            pass
        return None

    def _build_legend(self):
        while self._legend.count():
            child = self._legend.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for biome, col in sorted(self._biome_legend.items()):
            dot = QLabel()
            dot.setObjectName("legend_dot")
            dot.setStyleSheet(f"background: #{col.name().lstrip('#')}; "
                              f"border-radius: 5px; min-width: 10px; min-height: 10px;")
            self._legend.addWidget(dot)
            label = QLabel(biome)
            label.setStyleSheet("font-size: 8pt; padding-left: 2px; padding-right: 8px;")
            self._legend.addWidget(label)

    def _zoom_in(self):
        self.view.scale(1.4, 1.4)

    def _zoom_out(self):
        self.view.scale(0.7, 0.7)

    def _fit_all(self):
        if not self._items:
            return
        xs = [x for x, y, *_ in self._items]
        ys = [y for x, y, *_ in self._items]
        margin = 60
        rect = QRectF(
            min(xs) - margin, min(ys) - margin,
            (max(xs) - min(xs)) + margin * 2,
            (max(ys) - min(ys)) + margin * 2,
        )
        self.view.setSceneRect(rect)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            return super().wheelEvent(event)
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.view.scale(factor, factor)
        event.accept()


# ─── About Dialog ────────────────────────────────────────────────

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Barotrauma Save Viewer</b>"))
        layout.addWidget(QLabel("Parses .save files and displays structured data."))
        layout.addWidget(QLabel("Characters, hulls, items, missions, and campaign data."))
        layout.addWidget(QLabel("Ctrl+O Open | Ctrl+E Export JSON | Esc Clear"))
        btn = QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ─── Main Window ─────────────────────────────────────────────────

class SaveViewer(QMainWindow):
    """PySide6 save file viewer."""

    def __init__(self):
        super().__init__()
        self.sf: SaveFile | None = None
        self.file_path: Path | None = None

        self.setWindowTitle("Barotrauma Save Viewer")
        self.resize(1300, 820)

        self._build_menu()
        self._build_central()
        self._setup_shortcuts()
        self.setAcceptDrops(True)
        self._apply_dark_theme()

        recent = _load_recent()
        self.sidebar.update_recent(recent)
        self.statusBar().showMessage("Ready. Drop a .save file to begin.")

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        self.sidebar = Sidebar()
        self.sidebar.open_signal.connect(self._on_open)
        self.sidebar.clear_signal.connect(self._on_clear)
        self.sidebar.recent_click.connect(self._on_file_selected)
        splitter.addWidget(self.sidebar)

        self.tabs = QTabWidget()
        self.chars_widget = CharactersWidget()
        self.sub_widget = SubmarineWidget()
        self.hulls_widget = HullsWidget()
        self.items_widget = ItemsWidget()
        self.map_widget = MapWidget()
        self.campaign_widget = CampaignWidget()
        self.missions_widget = MissionsWidget()
        self.xml_widget = RawXmlWidget()

        self.tabs.addTab(self.chars_widget, "Characters")
        self.tabs.addTab(self.sub_widget, "Submarine")
        self.tabs.addTab(self.hulls_widget, "Hulls")
        self.tabs.addTab(self.items_widget, "Items")
        self.tabs.addTab(self.map_widget, "Map")
        self.tabs.addTab(self.campaign_widget, "Campaign")
        self.tabs.addTab(self.missions_widget, "Missions")
        self.tabs.addTab(self.xml_widget, "Raw XML")

        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([290, 1010])

        main_layout.addWidget(splitter)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Open Save File... (Ctrl+O)", self._on_open)
        file_menu.addAction("Export &JSON... (Ctrl+E)", self._on_export_json)
        file_menu.addAction("E&xport CSV...", self._on_export_csv)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("&Map", lambda: self.tabs.setCurrentWidget(self.map_widget))
        view_menu.addAction("&Raw XML", lambda: self.tabs.setCurrentWidget(self.xml_widget))
        view_menu.addAction("C&lear", self._on_clear)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._on_about)

    def _setup_shortcuts(self):
        a1 = QAction(self)
        a1.setShortcut(QKeySequence("Ctrl+O"))
        a1.triggered.connect(self._on_open)
        self.addAction(a1)

        a2 = QAction(self)
        a2.setShortcut(QKeySequence("Ctrl+E"))
        a2.triggered.connect(self._on_export_json)
        self.addAction(a2)

        a3 = QAction(self)
        a3.setShortcut(QKeySequence("Escape"))
        a3.triggered.connect(self._on_clear)
        self.addAction(a3)

    def _apply_dark_theme(self):
        self.setStyleSheet(DARK_STYLE)

    # ── Drag and drop ───────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".save"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self._on_file_selected(url.toLocalFile())
            return

    # ── File actions ────────────────────────────────────

    def _on_open(self):
        default_dir = str(
            Path.home() / "AppData" / "LocalLow" / "Eyefish" / "Barotrauma" / "saves"
        )
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Barotrauma Save File",
            default_dir,
            "Save files (*.save);;All files (*.*)",
        )
        if filepath:
            self._on_file_selected(filepath)

    def _on_file_selected(self, filepath: str):
        path = Path(filepath)
        if not path.exists():
            self.statusBar().showMessage(f"File not found: {path.name}")
            return

        self.file_path = path
        try:
            self.sf = parse_save(path)
            self._update_all()
            self.statusBar().showMessage(
                f"Loaded: {path.name} | {len(self.sf.characters)} chars "
                f"| {len(self.sf.hulls)} hulls | {len(self.sf.items)} items | "
                f"{len(self.sf.missions)} missions"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}")
            QMessageBox.warning(self, "Parse Error", str(e))
            self.sf = None
            return

        recent = _load_recent()
        fp = str(path.resolve())
        if fp not in recent:
            recent.insert(0, fp)
            if len(recent) > 10:
                recent = recent[:10]
            _save_recent(recent)
        self.sidebar.update_recent(recent)

    def _on_clear(self):
        self.sf = None
        self.file_path = None
        self._update_all()
        self.statusBar().showMessage("Ready. Drop a .save file to begin.")

    # ── Export ──────────────────────────────────────────

    def _on_export_json(self):
        if not self.sf:
            return
        initial = str(self.file_path.parent / f"{self.file_path.stem}.json") if self.file_path else ""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export to JSON", initial,
            "JSON files (*.json);;All files (*.*)",
        )
        if filepath:
            self._write_json(filepath)

    def _on_export_csv(self):
        if not self.sf:
            return
        initial = str(self.file_path.parent / f"{self.file_path.stem}-chars.csv") if self.file_path else ""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Characters to CSV", initial,
            "CSV files (*.csv);;All files (*.*)",
        )
        if filepath:
            self._write_csv(filepath)

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
        self.statusBar().showMessage(f"Exported JSON: {Path(filepath).name}")

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
        self.statusBar().showMessage(f"Exported CSV: {Path(filepath).name}")

    # ── Update display ──────────────────────────────────

    def _update_all(self):
        if not self.sf:
            self._update_empty()
            return
        self._update_stats()
        self._refresh_tables()

    def _update_empty(self):
        self.sidebar.update_stats("No file loaded")
        self.chars_widget.set_data([])
        self.sub_widget.set_data(None, 0, 0)
        self.hulls_widget.set_data([])
        self.items_widget.set_data([])
        self.map_widget.set_data([])
        self.campaign_widget.set_data(SaveFile(path=Path(".")))
        self.missions_widget.set_data([])
        self.xml_widget.set_data(None)

    def _update_stats(self):
        sf = self.sf
        if not sf:
            return
        name = sf.submarine.name or "Unknown"
        hp = (f"{sf.submarine.sub_type}/{sf.submarine.class_}"
              if sf.submarine.sub_type != "Unknown" else "")
        tier = (f"tier {sf.submarine.tier}"
                if sf.submarine.tier != "Unknown" else "")
        size = f"{sf.original_size:,}B / {sf.decompressed_size:,}B"
        alive = sum(1 for c in sf.characters if not c.permanently_dead)
        dead = sum(1 for c in sf.characters if c.permanently_dead)

        stats = (f"  Sub: {name}\n"
                 f"     {hp} | {tier}\n"
                 f"  Size: {size}\n"
                 f"  Chars: {len(sf.characters)}  ({alive} alive, {dead} dead)\n"
                 f"  Hulls: {len(sf.hulls)} | Structures: {len(sf.structures)}\n"
                 f"  Items: {len(sf.items)}\n"
                 f"  Locations: {len(sf.locations)}\n"
                 f"  Missions: {len(sf.missions)}")
        self.sidebar.update_stats(stats)

    def _refresh_tables(self):
        if not self.sf:
            return
        sf = self.sf
        self.chars_widget.set_data(sf.characters)
        self.sub_widget.set_data(sf.submarine, sf.original_size, sf.decompressed_size)
        self.hulls_widget.set_data(sf.hulls)
        self.items_widget.set_data(sf.items)

        # Map: pass locations and submarine position if available
        sub_pos = None
        if sf.submarine.dimensions and sf.submarine.dimensions != "Unknown":
            # Submarine position isn't stored in submarine info;
            # characters may have positions on the world map,
            # but submarine position is in gamesession metadata.
            # We'll center the map around the campaign locations.
            pass
        self.map_widget.set_data(sf.locations, sub_pos)

        self.campaign_widget.set_data(sf)
        self.missions_widget.set_data(sf.missions)
        self.xml_widget.set_data(sf.raw_xml)

    def _on_about(self):
        dlg = AboutDialog(self)
        dlg.exec()


# ─── Dark theme ──────────────────────────────────────────────────

DARK_STYLE = """
QMainWindow { background-color: #1e1e2e; }
QWidget { color: #cdd6f4; background-color: #1e1e2e; }

QTabWidget::pane {
    border: 1px solid #45475a;
    background-color: #1e1e2e;
    top: -1px;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #45475a;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #45475a;
    color: #89b4fa;
}
QTabBar::tab:hover { background-color: #45475a; }

QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    border: 1px solid #45475a;
    gridline-color: #313244;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QTableWidget::item { padding: 4px; }
QHeaderView::section {
    background-color: #313244;
    color: #bac2de;
    padding: 6px;
    border: 1px solid #45475a;
    font-weight: bold;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover { background-color: #45475a; }
QPushButton:pressed { background-color: #585b70; }

QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
    border: 1px solid #45475a;
}

QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
QTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
}

QLabel { color: #cdd6f4; }
QMenuBar { background-color: #1e1e2e; color: #cdd6f4; }
QMenuBar::item:selected { background-color: #45475a; }
QMenu { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; }
QMenu::item:selected { background-color: #45475a; }
QStatusBar {
    background-color: #313244;
    color: #bac2de;
    border-top: 1px solid #45475a;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #1e1e2e;
    width: 12px; height: 12px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 6px;
    min-height: 20px; min-width: 20px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background-color: #45475a; width: 1px; }

QGroupBox {
    border: 1px solid #45475a;
    border-radius: 4px;
    margin-top: 8px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QDialog { background-color: #1e1e2e; }
QScrollArea { border: none; }
"""


# ─── Entry point ────────────────────────────────────────────────

def main() -> None:
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SaveViewer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
