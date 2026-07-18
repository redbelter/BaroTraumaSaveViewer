---
# Barotrauma Save File Parser

## Goal
Parse Barotrauma save files (`.save`) and extract game state including characters, submarine layout, locations, missions.

## File Structure

### .save archives contain:
- `gamesession.xml` — campaign data, characters on sub, missions, locations
- `.sub` files — submarine templates (`noitems="true"`) or active sub with hull/structure/item data
- `CharacterData.xml` (optional external companion)

### Active Submarine Detection
```python
# In gamesession.xml:
<Gamesession ... submarine="Typhon">
```

Template subs have `noitems="true"` — skip these when looking for actual layout data.

## Key Parsers

### decode.py pipeline
1. Decompress gzip `.save` → binary archive
2. Parse archive entries → files (gamesession, .sub, CharacterData)
3. Extract active sub name from `<Gamesession submarine="...">`
4. Load hull/structure/gap/item data from active `.sub`

### parse.py conversion
- XML → dataclasses: SaveFile, SubmarineInfo, Character, Hull, Structure, Gap, Item, Mission, Location

## Gotchas

| Problem | Fix |
|---------|-----|
| CharacterData XML starts with UTF-8 BOM (`\ufeff`) | `xml_str.lstrip("\ufeff")` before parsing |
| Some items only have "x,y" position (no w,h) | Draw as dots, use default size |
| `campaign.location.id` may be missing | Fall back to None for sub position |

## Dataclasses
- **Character**: species, personality, skills(dict), talents(list), wallet_balance, salary, experience, afflictions(list), missions_completed
- **Structure/Gap/Item**: id, name, struct_type, position(x,y,w,h), size(w,h), condition, parent_id

## Test Files
- `tests/test_parser.py` — 47 unit tests for parse functions
- `tests/test_save_files.py` — 36 integration tests (full pipeline)
- `tests/test_widgets.py` — 6 widget interaction tests

## Build
```bash
taskkill /F /IM reverse-baro.exe 2>/dev/null
PYTHONPATH=src pytest tests/
PYTHONPATH=src .venv/Scripts/pyinstaller --clean -y reverse-baro.spec
```