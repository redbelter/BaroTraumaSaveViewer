"""Tests for Map zoom, ShipLayout zoom, and click behavior."""

import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QWheelEvent, QMouseEvent, QMouseEvent, QGuiApplication

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.data import Mission, Location, Structure
from gui import MapWidget, ShipLayoutWidget

pytest.importorskip("PySide6.QtWidgets")
_app_instance = None


def _ensure_app():
    global _app_instance
    if not _app_instance:
        _app_instance = QApplication.instance() or QApplication(sys.argv)
    return _app_instance


def _wheel(pos):
    return QWheelEvent(
        pos, pos,
        QPoint(0, -12), QPoint(0, 120),
        Qt.NoButton, Qt.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False,
    )


def _mouse_event(evtype, pos, button):
    return QMouseEvent(evtype, pos, pos, button, Qt.NoButton, Qt.NoModifier)


@pytest.fixture(autouse=True)
def _app():
    _ensure_app()
    QApplication.processEvents()


# ── Map tests ──

def test_map_data_and_auto_zoom():
    w = MapWidget()
    w.set_data(
        [
            Location(name="A", location_type="depot", biome="Ocean", position="100,200", index=0),
            Location(name="B", location_type="island", biome="Ocean", position="300,400", index=1),
        ],
        (100.0, 200.0),
        [],
    )
    assert len(w._items) == 2
    assert w._loc_by_index[0].name == "A"
    assert w.view.transform().m11() != 0


def test_map_zoom_via_wheel():
    w = MapWidget()
    w.set_data([Location(name="X", location_type="depot", biome="Ocean", position="0,0", index=0)], None, [])
    before = w.view.transform().m11()
    QApplication.postEvent(w, _wheel(w.rect().center()))
    QApplication.processEvents()
    assert w.view.transform().m11() > before


def test_map_scroll_alive_after_zoom():
    w = MapWidget()
    w.set_data(
        [
            Location(name="A", location_type="depot", biome="Ocean", position="0,0", index=0),
            Location(name="B", location_type="mining", biome="Caves", position="100,200", index=1),
        ],
        (0.0, 0.0), [],
    )
    for _ in range(5):
        QApplication.postEvent(w, _wheel(w.rect().center()))
        QApplication.processEvents()
    assert w.view.verticalScrollBar() is not None
    assert w.view.horizontalScrollBar() is not None


# ── Ship Layout tests ──

def test_ship_zoom_via_wheel():
    w = ShipLayoutWidget()
    w.set_data([], [], [], [])
    before = w.view.transform().m11()
    QApplication.postEvent(w.view.viewport(), _wheel(w.view.viewport().rect().center()))
    QApplication.processEvents()
    assert w.view.transform().m11() > before


def test_ship_double_click_shows_detail():
    w = ShipLayoutWidget()
    w.set_data(
        [],
        [Structure(id="1", name="corridor", struct_type="Wall", position="100,100,50,10", size="50,10")],
        [], [],
    )
    items_with_tt = [i for i in w.scene.items() if i.toolTip()]
    assert items_with_tt, "expected at least one tooltip item"
    item = items_with_tt[0]
    view_pos = w.view.mapFromScene(item.boundingRect().center())
    vp = w.view.viewport()
    # Send a double-click event (the eventFilter checks MouseButtonDblClick, not two presses)
    QApplication.postEvent(vp, _mouse_event(QEvent.Type.MouseButtonDblClick, view_pos, Qt.LeftButton))
    QApplication.processEvents()
    assert "corridor" in w._ship_detail.text().lower()


def test_ship_scroll_alive_after_zoom():
    w = ShipLayoutWidget()
    w.set_data([], [], [], [])
    vp = w.view.viewport()
    for _ in range(10):
        QApplication.postEvent(vp, _wheel(vp.rect().center()))
        QApplication.processEvents()
    assert w.view.verticalScrollBar() is not None
    assert w.view.horizontalScrollBar() is not None
    s = w.view.transform().m11()
    assert 0 < abs(s) < 1e10


if __name__ == "__main__":
    _ensure_app()
    for n, f in sorted((k, v) for k, v in globals().items() if k.startswith("test_")):
        try:
            f()
            print(f"  PASS  {n}")
        except Exception as e:
            print(f"  FAIL  {n}: {e}")