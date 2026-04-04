# Save File Analysis Report: "potato 2.save"

## Overview
This document analyzes the binary save file format used by the game *Outer Wilds* or a similar submarine-themed game that uses the "Submarine" game framework.

## File Information
- **Filename**: `potato 2.save`
- **Original Size**: 191,197 bytes (approximately 187 KB)
- **File Type**: Gzip-compressed nested binary archive

## Compression Structure

### Level 0: Original File
- Contains gzip compression (magic bytes: `1f 8b 08 00`)
- Single compressed stream
- Decompresses to: 412,517 bytes

### Level 1: First Decompression
- Contains multiple embedded gzip streams at positions:
  - Position 0: Another gzip stream (different header format)
  - Position 298,138: Main content gzip stream
  - Additional positions: Other data blocks

### Level 2: Main Content Stream
- **Stream 1** (at position 298,138) decompresses to: 2,076,862 bytes (approximately 2 MB)
- This contains the actual game save data in XML format

## File Format Analysis

### Header Information
```
First bytes: 1f 8b 08 00 00 00 00 00 00 0a
Description: Standard gzip header with DEFLATE compression
```

### Content Type
- **Primary Format**: XML (Extensible Markup Language)
- **Application**: Submarine game save data
- **Game Version**: 1.11.5.0

### Main Data Structure
The main content is an XML document starting with:
```xml
<Submarine 
    description="R-29 is a heavyweight transport ship..." 
    checkval="1604291146" 
    price="16500" 
    tier="2" 
    type="Player"
    class="Transport"
    gameversion="1.11.5.0"
    dimensions="5520,1506"
    cargocapacity="60">
```

### Key Subsystems Found in XML
1. **Submarine Configuration**
   - R-29 heavy transport ship
   - Transport class
   - 60 cargo capacity
   - Crew requirements: 5-9 members (high experience recommended)

2. **Security Systems**
   - "Safe and Sound Security 101" terminal
   - Traitor disciplinary guidelines
   - Level 1-3 offense classifications

3. **Outfitting Items**
   - Multiple items with detailed attributes
   - Inventory management data
   - Item conditions and states

## Technical Details

### Compression Method
- Primary compression: Gzip/DEFLATE algorithm
- Nested compression: Multiple gzip streams within decompressed data

### Text Encoding
- UTF-16 encoding detected in some sections
- XML content uses standard ASCII/UTF-8

### File Organization
```
potato 2.save (191 KB gzip)
│
└── Level 0 decompress → 412 KB
    │
    ├── Embedded gzip stream 0 → [different format, error]
    │
    ├── Other data blocks
    │
    └── Main content gzip stream (pos 298,138) → 2 MB
        │
        └── XML game save data
```

## Analysis Tools Created
- `analyze_save.py`: Initial file analysis and decompression
- `deep_analysis.py`: Multi-level gzip stream extraction
- Various output files with decompressed content

## Recommendations for Further Analysis
1. Examine all embedded gzip streams
2. Parse the XML structure completely
3. Identify any encryption or checksum mechanisms (checkval field suggests validation)
4. Map the complete item inventory and save state

## Conclusion
The "potato 2.save" file is a game save for a submarine-themed game using a nested compression scheme with gzip streams embedded within each other. The main content is XML-formatted data describing a R-29 transport submarine, its outfitting, crew configuration, and security systems.
