# BaroTrauma Save File Viewer

A powerful Python-based tool for analyzing and extracting data from Barotrauma save files. This repository contains multiple utilities for inspecting, comparing, and exporting game data.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Main Applications

### 1. `save_file_viewer.py` - **Primary Save File Viewer** ⭐ RECOMMENDED
A feature-rich GUI application with:
- ✅ Multi-layer decompression of Barotrauma's nested gzip format
- ✅ Character analysis: ID, Name, Job, Health condition, Position
- ✅ Statistics dashboard with compression and submarine info
- ✅ Filterable crew manifest table
- ✅ Export to XML functionality

**Recommended for most users!**

### 2. `save_compare_tool.py` - **Save File Comparator**
Compare two save files to see differences:
- Mission changes between saves
- Character name comparison
- Mission count analysis
- Added/removed mission tracking

## 📋 Requirements

- Python 3.8 or higher
- No external dependencies (uses only standard library modules)

### Standard Library Modules Used:
- `tkinter` - GUI framework
- `gzip`, `zlib` - Decompression
- `xml.etree.ElementTree` - XML parsing
- `pathlib`, `collections`

## 🛠 Installation

1. Clone or download this repository
2. Ensure Python 3.8+ is installed
3. Run the main viewer:

```bash
python save_file_viewer.py
```

Or use the comparison tool:
```bash
python save_compare_tool.py
```

## 🔍 Usage Guide

### For `save_file_viewer.py` (Main Application)

**Opening a Save File:**
1. Click **File → Open Save File** to browse and select a `.save` file
2. Or click "Load File" button after selecting a file path

**Viewing Data:**
- **Characters Tab**: View crew manifest with job filtering
- **Save File Info Tab**: Compression details and submarine configuration
- **XML Preview Tab**: Raw XML content from the save file

**Exporting Data:**
1. After loading, "Export to XML" becomes enabled
2. Click **File → Export to XML**
3. Choose location and filename

### For `save_compare_tool.py` (Comparison Tool)

**Comparing Two Saves:**
1. Run the tool from command line
2. Select two save files from dropdown menus
3. Click "Compare" to see differences

## 📖 File Format Documentation

Barotrauma save files use a multi-layer compression format:

- **Level 0**: Outer gzip container with filename header
- **Level 1+**: Multiple nested gzip streams containing XML data
- Only streams with `compression method = 0x08` (deflate) are valid
- Application searches all valid streams to find most complete game state

See [SAVE_FILE_FORMAT.md](SAVE_FILE_FORMAT.md) for detailed technical documentation.

## 🧪 Utility Scripts

The repository also contains various analysis and testing scripts. Here's a quick overview:

| File | Purpose | Status |
|------|---------|--------|
| `analyze_*.py` (various) | Save file analysis tools | 🔧 Testing/Debugging |
| `check_*.py` (various) | Validation and header checking | 🔧 Testing/Debugging |
| `compare_*.py` | File comparison utilities | 🔧 Testing/Debugging |
| `extract_characters.py` | Character extraction | ⚠️ Redundant - use save_file_viewer.py |
| `parse_characters.py` | Parse character data | ⚠️ Redundant - use save_file_viewer.py |

**Redundant Files (Can be removed):**
- `extract_characters.py` - Superseded by save_file_viewer.py
- `parse_characters.py` - Superseded by save_file_viewer.py
- Most `analyze_*.py`, `check_*.py`, and `compare_*.py` files were development scripts

## 🏗️ Technical Details

### Save File Structure
```
[File Header] → [Gzip Stream #1] → [Data] → [Gzip Stream #2] → ...
     |                    |                   |
   UTF-16             Deflate            Deflate
  filename          (XML content)       (XML content)
```

### Character Data Format
```python
{
    'id': int,
    'name': str,
    'job': str,
    'condition': "XX.XX%",  # Health condition percentage
    'rect': str            # Position coordinates
}
```

## 📁 Directory Structure

```
reverse-baro/
├── save_file_viewer.py       # Main GUI application ⭐ RECOMMENDED
├── save_compare_tool.py      # Comparison tool
├── SAVE_FILE_FORMAT.md       # Technical documentation
├── README.md                 # This file
├── LICENSE                   # MIT License
├── *.save                    # Sample save files (example data)
└── newer-saves/              # Additional test saves
```

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Barotrauma development team for creating an amazing game
- Community for save file format research and documentation

---

*Built with ❤️ using Python and Tkinter*
