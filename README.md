# Barotrauma Save File Viewer

A powerful Python-based tool for analyzing and extracting data from Barotrauma save files. This application provides detailed insights into submarine configurations, crew manifest, missions, and game state.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

- **Browse & Select Save Files** - Easy file dialog for selecting `.save` files from any location
- **Multi-Layer Decompression** - Handles Barotrauma's nested gzip compression automatically
- **Character Analysis** - View complete crew manifest with:
  - Character ID, Name, and Job
  - Health condition percentage
  - Position information (rect)
- **Statistics Dashboard** - Comprehensive stats including:
  - File size and compression details
  - Submarine configuration info
  - Crew count by job
- **Export Functionality** - Export character data to structured XML files
- **Clean GUI Interface** - Tab-based interface with filtering capabilities

## 📋 Requirements

- Python 3.8 or higher
- No external dependencies (uses only standard library modules)

### Standard Library Modules Used:
- `tkinter` - GUI framework
- `gzip` - Outer layer decompression
- `zlib` - Inner gzip stream decompression
- `xml.etree.ElementTree` - XML parsing
- `pathlib` - Path handling
- `collections.defaultdict` - Data aggregation

## 🛠 Installation

1. Clone or download this repository
2. Ensure Python 3.8+ is installed on your system
3. Run the application:

```bash
python save_file_viewer.py
```

## 🔍 Usage

### Opening a Save File
1. Launch the application
2. Click **File → Open Save File** to browse and select a `.save` file
3. Or click the "Load File" button after selecting a file

### Viewing Data
- **Characters Tab**: View crew manifest with filter by job
- **Save File Info Tab**: Detailed compression and file structure information
- **XML Preview Tab**: Raw XML content from the save file

### Exporting Data
1. After loading a save file, the "Export to XML" menu item becomes enabled
2. Click **File → Export to XML**
3. Choose the export location and filename

## 📖 File Format Documentation

Barotrauma save files use a complex multi-layer compression format:

- **Level 0**: Outer gzip container
- **Level 1+**: Multiple nested gzip streams containing XML data
- Only streams with `compression method = 0x08` (deflate) are valid
- The application searches all valid streams to find the most complete game state

See [SAVE_FILE_FORMAT.md](SAVE_FILE_FORMAT.md) for detailed technical documentation.

## 🏗️ Technical Details

### Save File Structure
```
[File Header] → [Gzip Stream #1] → [Data] → [Gzip Stream #2] → ...
     |                    |                   |
   UTF-16             Deflate            Deflate
  filename          (XML content)       (XML content)
```

### Character Extraction
Characters are stored in duffelbag items with the following data:
```python
{
    'id': int,
    'name': str,
    'job': str,
    'condition': "XX.XX%",  # Health condition percentage
    'rect': str            # Position coordinates
}
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Barotrauma development team for creating an amazing game
- The community for save file format research and documentation

---

*Built with ❤️ using Python and Tkinter*

## 📂 Project Structure

```
BaroTraumaSaveViewer/
├── save_file_viewer.py        # Main application (GUI tool)
├── save_compare_tool.py       # Compare multiple save files
├── SAVE_FILE_FORMAT.md        # Technical documentation
├── README.md                  # This file
└── LICENSE                    # MIT License

# Development/Analysis Scripts (can be removed):
├── analyze_*.py               # Various analysis scripts
├── check_*.py                 # Validation scripts  
├── test_*.py                  # Test scripts
├── extract_*.py               # Extraction utilities
├── compare_*.py               # Comparison tools
└── find_*.py                  # Discovery utilities
```

## 🧹 Cleanup Notes

This repository contains many development and analysis scripts that were used during reverse engineering. The following categories can be safely removed if you only need the final tools:

- **`analyze_*.py`** (13 files) - Analysis scripts for exploring file structure
- **`check_*.py`** (5 files) - Validation and header checking utilities  
- **`test_*.py`** (9 files) - Test scripts during development
- **`extract_*.py`** (3 files) - Early extraction utilities
- **`compare_*.py`**, **`find_*.py`**, etc. - Various utility scripts

Keep only:
- `save_file_viewer.py` - Main application
- `save_compare_tool.py` - Save comparison tool  
- `SAVE_FILE_FORMAT.md` - Documentation
