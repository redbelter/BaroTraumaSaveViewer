---
# PySide6 Headless Widget Testing

## Goal
Test PySide6 widgets (MapWidget, ShipLayoutWidget, etc.) in pytest without showing windows.

## Setup
```python
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QWheelEvent, QMouseEvent

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture(autouse=True)
def _app():
    if not QApplication.instance():
        QApplication(sys.argv)
    QApplication.processEvents()
```

## Key Patterns

### 1. Wheel Event
```python
def _wheel(pos):
    return QWheelEvent(
        pos, pos,
        QPoint(0, -12), QPoint(0, 120),
        Qt.NoButton, Qt.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False,
    )
```

### 2. Mouse Event  
```python
def _mouse_event(evtype, pos, button):
    return QMouseEvent(evtype, pos, pos, button, Qt.NoButton, Qt.NoModifier)
```

### 3. Post Events
```python
QApplication.postEvent(w.view.viewport(), _wheel(vp.rect().center()))
QApplication.processEvents()
```

## Common Pitfalls

| Problem | Fix |
|---------|-----|
| `event.pos()` deprecated | Use `event.position().toPoint()` |
| Wheel on widget, not viewport | ShipLayoutWidget filters viewport's wheel events |
| `mapToScene()` returns `QPointF` | Pass directly to `itemAt(scene_pos)` |
| `itemAt()` expects `QPoint` | Don't pass `QPointF`, convert with `.toPoint()` |
| Double-click needs `MouseButtonDblClick` | Not two `MouseButtonPress` events |
| `ScrollPhase.Begin` missing | Use `NoScrollPhase` |

## Example Test
```python
def test_ship_double_click_shows_detail():
    w = ShipLayoutWidget()
    w.set_data([], [Structure(...)], [], [])
    items_with_tt = [i for i in w.scene.items() if i.toolTip()]
    assert items_with_tt
    item = items_with_tt[0]
    view_pos = w.view.mapFromScene(item.boundingRect().center())
    vp = w.view.viewport()
    QApplication.postEvent(vp, _mouse_event(QEvent.Type.MouseButtonDblClick, view_pos, Qt.LeftButton))
    QApplication.processEvents()
    assert "corridor" in w._ship_detail.text().lower()
```