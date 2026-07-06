# Handoff Notes — reverse-baro Session (July 2026)

## What's Done
- **PySide6 GUI** with tabs: Characters, Submarine, Hulls, Items, Map, Ship Layout, Campaign, Missions, Raw XML
- **Map tab** — world map with biome-colored dots, mission route lines, clickable locations, proper legend
- **Ship Layout tab** — interior submarine map from structure rects, color-coded by type
- **Character file loading** — "Load Characters..." button in sidebar, merges with save data
- **Submarine position** on map — derived from `campaign.location.id` metadata → location coords
- **Map zoom** fixed — relative 10% margin instead of fixed 60px
- **Window title** updates with sub name + loaded filename
- **Submarine icon** generated (assets/app_icon.ico) — set on app and window level
- **PyInstaller build** ready (dist/reverse-baro/reverse-baro.exe) — double-click runs
- **83/83 tests** pass (pytest)

## Current State
- **Commit:** `639df7e` — cleanup just pushed
- Clean working tree, no pending changes
- Virtualenv at `.venv/` (Python 3.11/3.12)
- `PYTHONPATH=src` required for imports

## Key Files
- `src/gui.py` — main GUI (~1600 lines), all widgets
- `src/parser/parse.py` — XML → dataclass conversion
- `src/parser/decode.py` — .save file decompression + pipeline
- `src/parser/data.py` — dataclasses (SaveFile, Character, Hull, etc.)
- `pyproject.toml` — deps: pyside6>=6.6.0
- `reverse-baro.spec` — PyInstaller config (onedir build)
- `build.bat` — one-command Windows build: `pyinstaller --clean -y reverse-baro.spec`

## Known Issues / TODOs
1. **Ship Layout tab**: Item position parsing assumes rect format "x,y,w,h" but some items only have "x,y" — they're drawn as dots but may be misplaced
2. **Character parsing**: `parse_character_data` skips permanently dead characters — some users may want to see them
3. **Sub position**: Falls back to campaign.location.id lookup. If that's missing, position is still None (no third fallback)
4. **Tests**: No GUI-level tests (widgets instantiated in test but only basic checks). Visual/UI bugs won't be caught by pytest
5. **Cron jobs**: Discord delivery was tested from CLI. Jobs scheduled in CLI are LOCAL-ONLY — not delivered back

## Build/Push Workflow
```
PYTHONPATH=src pytest tests/  # verify
pyinstaller --clean -y reverse-baro.spec  # rebuild exe
git add -A && git commit -m "..." && git push origin main  # push
```

## Discord Integration
Configured in `config.yaml` — platform `discord` with channel `1523167625729933435`, working. Cron jobs can deliver to `discord:1523167625729933435`.
