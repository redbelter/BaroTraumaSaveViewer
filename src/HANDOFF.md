# reverse-baro — Handoff Notes (July 2026)

## Repo State
- **Branch:** main → origin/main
- **Working tree:** Unstaged changes — NOT COMMITTED
- **Venv:** `.venv/` (Python 3.12), Python at `.venv/Scripts/python.exe`
- **Test:** `PYTHONPATH=src pytest tests/` — 83/83 pass
- **Build:** `PYTHONPATH=src .venv/Scripts/pyinstaller --clean -y reverse-baro.spec`
- **BLOCKER:** Must `taskkill /F /IM reverse-baro.exe 2>/dev/null` before building — locks qico.dll

## Unstaged Changes

### 1. Active Sub Detection — `src/parser/decode.py`
- Reads `submarine="Typhon"` attr from `<Gamesession>` in gamesession.xml
- Skips non-active .sub template files (noitems="true")
- Old code merged all .sub files → wrong sub name, inflated hull/struct counts
- `tests/test_parser.py`: assertions changed "Camel" → "Orca2"

### 2. BOM Fix — `src/parser/parse.py` line 468
- Added `xml_src = xml_src.lstrip("\ufeff")` before startswith check
- BOM not stripped by .strip(), caused ET.parse() on string-as-filename → silent 0 chars

### 3. Enriched Character Dataclass — `src/parser/data.py`
Added fields to Character:
- species (str), personality (str)
- skills (dict[str, float]), talents (list[str]), afflictions (list[str])
- wallet_balance, salary, experience, missions_completed (int)

### 4. Char Detail Extraction — `src/parser/parse.py` `_extract_char_details()`
New helper extracts species, personality, skills, talents, wallet, salary,
experience, missions completed, afflictions from XML.
All 3 parse locations updated: parse_characters_from_xml, parse_campaign loop,
parse_character_data.

### 5. QPolygonF Fix — `src/gui.py` line 762
Raw tuples → QPointF() for PySide6 compatibility. Added QPointF, QPoint imports.

### 6. Ship Layout Zoom — `src/gui.py` ShipLayoutWidget
- Toolbar: +, -, Fit buttons
- eventFilter on `self.view.viewport()` for wheel zoom (NOT self.view — wheel events go to viewport)
- Filter checks both self.view AND self.view.viewport() in obj condition

### 7. Ship Item Tooltips — `src/gui.py`
setToolTip() + setAcceptHoverEvents(True) on structures, gaps, items.

### 8. Map Auto-Zoom — `src/gui.py` MapWidget set_data
When submarine_pos available, zooms to 800x800 area centered on sub.

### 9. Character Detail Panel — `src/gui.py` CharactersWidget
Full rewrite of broken class. Detail panel below table. Row selection populates:
name/species, personality, status/hp, skill bars (█/░ blocks), talents,
afflictions, exp/wallet/missions. Dark theme frame.

### 10. .gitignore
Added data/real/ (user reference data).

## Still Needed

### Ship Click Detail Panel
Subagent was dispatched to add click-to-select showing item details in a panel
below the ship layout. Check if landed with `git diff src/gui.py` — look for
MouseButtonPress handling in eventFilter and a _ship_detail QLabel.

## Patterns
- Dark theme: bg #11131c, #181a24; borders #45475a; text #cdd6f4
- lowercase labels, concise style
- Event filters on viewport(), not self.view, for interactive events
- New dataclass fields MUST have defaults
- Parser uses .get() with defaults, never crashes on missing XML
- Tests verify data wiring, not visual UI

## File Map
| File | Purpose |
|------|---------|
| src/gui.py | Main GUI (~1740 lines) |
| src/parser/decode.py | .save extraction pipeline |
| src/parser/parse.py | XML → dataclass |
| src/parser/data.py | Dataclasses |
| tests/test_parser.py | 47 parser tests |
| tests/test_save_files.py | 36 GUI/integration tests |
