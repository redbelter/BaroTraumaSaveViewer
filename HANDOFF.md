# Handoff Notes — reverse-baro Session (July 2026)

## What's Done

- **PySide6 GUI** with tabs: Characters, Submarine, Hulls, Items, Map, Ship Layout, Campaign, Missions, Raw XML
- **Map tab** — world map with biome-colored dots, mission route lines, clickable locations, proper legend
- **Ship Layout tab** — interior submarine map from structure rects, color-coded by type, zoom controls (+/-/Fit), wheel zoom, double-click to select items and show detail panel, drag-pan
- **Character file loading** — "Load Characters..." button in sidebar, merges with save data
- **Characters detail panel** — click row to see skills (with bar chart), talents, afflictions, wallet, experience, missions completed, species, personality
- **Enriched Character dataclass** — species, personality, skills (dict), talents (list), wallet_balance, salary, experience, afflictions (list), missions_completed
- **Character data extraction** — `_extract_char_details()` pulls skills/talents/wallet/afflictions from XML at all 3 parse sites
- **Submarine position** on map — derived from `campaign.location.id` metadata → location coords
- **Map auto-zoom** — zooms in 800×800 area around submarine on load (removed broken `setSceneRect` that locked scroll)
- **Window title** updates with sub name + loaded filename
- **Submarine icon** generated (assets/app_icon.ico) — set on app and window level
- **Active submarine detection** — reads `submarine="..."` attr from `<Gamesession>`, skips template .sub refs (noitems="true")
- **BOM fix** — strips UTF-8 BOM from internal CharacterData XML
- **QPolygonF fix** — tuples → QPointF for PySide6 compatibility
- **PyInstaller build** ready (dist/reverse-baro/reverse-baro.exe) — double-click runs
- **89/89 tests** pass (pytest) — includes 6 new widget interaction tests (test_widgets.py)

## Current State

- **Last commit:** uncommitted changes in `src/gui.py` and new `tests/test_widgets.py`
- **Commit hash:** `a54aeaf` (on origin/main)
- **Branch:** main → origin/main
- **Unstaged changes:** ship click handler uses `event.position().toPoint()` instead of `event.pos()` (deprecated)
- **Virtualenv:** `.venv/` (Python 3.12), Python at `.venv/Scripts/python.exe`
- **Test cmd:** `PYTHONPATH=src pytest tests/`
- **Build cmd:** `taskkill /F /IM reverse-baro.exe 2>/dev/null` then `PYTHONPATH=src .venv/Scripts/pyinstaller --clean -y reverse-baro.spec`

## Key Files

- `src/gui.py` — main GUI (~1750 lines), all widgets
- `src/parser/parse.py` — XML → dataclass conversion
- `src/parser/decode.py` — .save file decompression + pipeline
- `src/parser/data.py` — dataclasses (SaveFile, Character with 9 new fields, Hull, etc.)
- `tests/test_parser.py` — 47 parser tests
- `tests/test_save_files.py` — 36 GUI widget + integration tests
- `tests/test_widgets.py` — 6 new widget interaction tests (map zoom, ship zoom, ship click, scroll alive)
- `pyproject.toml` — deps: pyside6>=6.6.0
- `reverse-baro.spec` — PyInstaller config (onedir build)

## Known Issues / TODOs

1. **Ship Layout tab**: Item position parsing assumes rect format "x,y,w,h" but some items only have "x,y" — they're drawn as dots but may be misplaced
2. **Character parsing**: `parse_character_data` skips permanently dead characters — some users may want to see them
3. **Sub position**: Falls back to campaign.location.id lookup. If that's missing, position is still None (no third fallback)
4. **Cron jobs**: Discord delivery was tested from CLI. Jobs scheduled in CLI are LOCAL-ONLY — not delivered back
5. **Ship click detail**: The `_restore_prev_pen()` restores previous highlight pen. When `set_data()` clears scene, it resets `_prev_highlight = None`. But if user clicks without hitting an item, nothing happens. Could add a "Background clicked, clearing selection" option.
6. **Map auto-zoom radius**: Currently hardcoded `radius = 400`. If submarine is in a large biome with far-flung locations, 400px may not show enough. Could compute radius from max distance to furthest location instead.

## Build/Push Workflow

```bash
taskkill /F /IM reverse-baro.exe 2>/dev/null  # MUST do this or build fails
PYTHONPATH=src pytest tests/                   # verify
PYTHONPATH=src .venv/Scripts/pyinstaller --clean -y reverse-baro.spec  # rebuild exe
git add -A && git commit -m "..." && git push origin main  # push
```

## Discord Integration

Configured in `config.yaml` — platform `discord` with channel `1523167625729933435`, working. Cron jobs can deliver to `discord:1523167625729933435`.

## Barotrauma Save Structure

- `.save` files are gzip archives containing:
  - `gamesession.xml` — campaign data, characters on sub, missions, locations
  - `.sub` files — submarine templates (noitems="true") and active sub
  - `CharacterData.xml` (sometimes internal, sometimes external companion file)
- External `_CharacterData.xml` companion files live alongside .save in the saves folder
- Active submarine identified by `submarine="SubName"` attribute on `<Gamesession>` in gamesession.xml
- Template .sub files have `noitems="true"`; only the active sub has actual hull/structure/item data
- CharacterData XML has UTF-8 BOM — must strip before parsing with `lstrip("\ufeff")`

## PySide6 Gotchas
- `event.pos()` is deprecated → use `event.position().toPoint()`
- QGraphicsView wheel events go to the **viewport**, not the view itself → install eventFilter on `viewport()`
- `setSceneRect()` before `fitInView()` can lock the scene bounds and break scrolling
- `QPolygonF` requires `QPointF` objects, not raw tuples
- `itemAt()` takes `QPoint`, not `QPointF`
- `mapToScene()` already returns `QPointF`
- Double-click detection: check for `QEvent.Type.MouseButtonDblClick`, not double `MouseButtonPress`
