# Barotrauma Save File Format

## Overview

Barotrauma save files are compressed archives that contain game state information including submarine configuration, crew members (characters), missions, and outpost data. The format uses **multiple nested gzip streams** with XML data containing the actual game state.

---

## File Structure

### Level 0: Outer Gzip Container

```
[File Header] [Gzip Stream #1] [Intermediate Data] [Gzip Stream #2] ... [Gzip Stream #N]
```

#### Header Format (26-30 bytes)
- **Bytes 0-3**: Little-endian integer indicating filename length (in characters)
- **Bytes 4+**: UTF-16 LE encoded filename with null terminator

#### Gzip Stream Structure

Each valid gzip stream has this structure:
```
[1f 8b] [08] [flags] [mtime] [xfl] [os] [DEFLATE data] [CRC32] [ISIZE]
```

- **Magic bytes**: `1f 8b` (gzip identifier)
- **Compression method**: Must be `08` (deflate) - this is CRITICAL
- **mtime, xfl, os**: Gzip metadata (typically zeros or defaults)
- **DEFLATE data**: Actual compressed content
- **CRC32 + ISIZE**: Gzip footer for integrity checking

**CRITICAL**: Only streams with `compression method = 0x08` are valid gzip streams. Other `1f 8b` patterns in the file are garbage/padding data.

---

## Stream Discovery Pattern

Barotrauma creates multiple gzip streams in the save file, but **not all are valid**:

| File Type | Valid Gzip Streams | Total `1f 8b` Markers |
|-----------|-------------------|----------------------|
| Original saves | Varies (3-6) | Often more due to garbage data |
| Copy/Played saves | Varies (2-4) | Often more due to garbage data |

### Valid vs Invalid Gzip Streams

**Valid gzip stream header**: `1f 8b 08 ...` (method = 0x08 for deflate)
**Invalid/garbage streams**: `1f 8b XX ...` where X != 08

### Example Analysis

**Original `potato 2.save`:**
- Total `1f 8b` markers: 6
- Valid gzip streams (method=0x08): 3
- Valid stream content:
  - Stream @ 28: Submarine XML, **0 characters** (template/backup)
  - Stream @ 314,440: Submarine XML, **0 characters**
  - Stream @ 404,912: Submarine XML, **21 characters** ← **Most complete state**

**Copy `potato 2-og.save`:**
- Total `1f 8b` markers: 3
- Valid gzip streams (method=0x08): 2
- Valid stream content:
  - Stream @ 28: Submarine XML, **0 characters** (template/backup)
  - Stream @ 267,852: Submarine XML, **6 characters** ← **Most complete state**

---

## CharacterData.xml Files

Some Barotrauma save files have a separate `CharacterData.xml` file alongside them. These files contain detailed character information that may not be fully present in the main save XML.

### File Relationship
- CharacterData.xml files are named after their associated save file: `{basename}_CharacterData.xml`
- **Only original saves have CharacterData.xml files** - copies (files with "copy" or "og" in the name) do NOT have separate character data files

---

## Stream Detection and Extraction

### The Critical Insight

You CANNOT assume which stream contains the game state. Different save files store their data at different stream positions. You must:

1. Find all `1f 8b` markers
2. **Only process streams where compression method = 0x08** (valid deflate)
3. Decompress each valid stream
4. Check which one contains "Submarine" XML
5. Select the stream with the **most characters** (most complete game state)

### Generic Detection Algorithm

```python
import gzip
import zlib
import xml.etree.ElementTree as ET

def find_submarine_xml(level0_data):
    """
    Find and return the Submarine XML from level 0 decompressed data.
    
    Returns the stream with the most characters (most complete game state).
    """
    
    best_result = None
    
    # Find all potential gzip positions
    for i in range(28, len(level0_data)):
        # CRITICAL: Only valid gzip streams have method = 0x08 (deflate)
        if level0_data[i] == 0x1f and level0_data[i+1] == 0x8b and level0_data[i+2] == 0x08:
            try:
                stream_data = level0_data[i:]
                
                # Decompress using gzip wrapper (MAX_WBITS|16)
                decompressed = zlib.decompress(stream_data, zlib.MAX_WBITS|16)
                
                # Try UTF-8 decode
                xml_text = decompressed.decode('utf-8')
                
                # Validate: must have XML tags AND Submarine content
                if '<' in xml_text and '>' in xml_text and 'Submarine' in xml_text:
                    root = ET.fromstring(xml_text)
                    char_count = len(root.findall('.//Item[@identifier="duffelbag"]'))
                    
                    # Keep track of best result (most characters = most complete state)
                    if not best_result or char_count > best_result['character_count']:
                        best_result = {
                            'position': i,
                            'decompressed_size': len(decompressed),
                            'xml_text': xml_text,
                            'root': root
                        }
                        
            except Exception as e:
                continue
    
    return best_result  # Returns None if no valid stream found

def extract_save_data(save_path):
    """
    Extract all game data from a Barotrauma save file.
    Works for both original and copy/played files.
    """
    
    # Step 1: Read and decompress outer layer
    with open(save_path, 'rb') as f:
        original = f.read()
    level0 = gzip.decompress(original)
    
    # Step 2: Find the best Submarine XML stream
    result = find_submarine_xml(level0)
    
    if not result:
        return None
    
    root = result['root']
    
    # Step 3: Extract all data from the found XML
    submarine = dict(root.attrib)
    
    characters = []
    for item in root.findall('.//Item[@identifier="duffelbag"]'):
        tags_str = item.get('Tags', '')
        
        name = None
        job = None
        
        for tag in [t.strip() for t in tags_str.split(',')]:
            if tag.startswith('name:'):
                name = tag[5:]
            elif tag.startswith('job:'):
                job = tag[4:]
        
        if name and job:
            characters.append({
                'id': int(item.get('ID', 0)),
                'name': name,
                'job': job,
                'condition': f"{float(item.get('conditionpercentage', '100')):.2f}%"
            })
    
    missions = []
    for mission in root.findall('.//missions/mission'):
        missions.append({
            'prefabid': mission.get('prefabid', ''),
            'destinationindex': mission.get('destinationindex', ''),
            'origin': mission.get('origin', '')
        })
    
    levels = []
    for level in root.findall('.//Level'):
        levels.append({
            'biome': level.get('biome', ''),
            'difficulty': level.get('difficulty', ''),
            'initialdepth': level.get('initialdepth', '')
        })
    
    return {
        'submarine': submarine,
        'characters': characters,
        'missions': missions,
        'levels': levels
    }
```

### Key Implementation Details

1. **Check compression method**: Only process `1f 8b 08` (not other `1f 8b` patterns)
2. **Decompress with gzip wrapper**: Use `zlib.decompress(..., zlib.MAX_WBITS|16)`
3. **Select best stream**: Choose the one with most characters (most complete state)

---

## Complete Save Data Extraction

### With CharacterData.xml Support

```python
import os

def extract_save_data_with_character_xml(save_path):
    """
    Enhanced extraction that also loads CharacterData.xml if available.
    """
    
    # First extract basic data from Submarine XML
    result = extract_save_data(save_path)
    if not result:
        return None
    
    # Check for associated CharacterData.xml
    base_name = save_path.replace('.save', '')
    char_xml_path = base_name + '_CharacterData.xml'
    
    if os.path.exists(char_xml_path):
        try:
            tree = ET.parse(char_xml_path)
            root_cd = tree.getroot()
            
            detailed_characters = []
            for ccd in root_cd.findall('CharacterCampaignData'):
                char_info = {
                    'name': '',
                    'inventory': [],
                    'health': {},
                    'wallet_balance': 0
                }
                
                # Basic info
                char_elem = ccd.find('Character')
                if char_elem is not None:
                    char_info['name'] = char_elem.get('name', '')
                    
                    job = char_elem.find('job')
                    if job is not None:
                        char_info['job'] = job.get('name', '')
                
                # Inventory
                inv_elem = ccd.find('inventory')
                if inv_elem is not None:
                    for item in inv_elem.findall('Item'):
                        char_info['inventory'].append({
                            'name': item.get('name', ''),
                            'ID': int(item.get('ID', 0))
                        })
                
                # Health
                health_elem = ccd.find('health')
                if health_elem is not None:
                    char_info['health']['limbs'] = len(health_elem.findall('LimbHealth'))
                    char_info['health']['afflictions'] = len(health_elem.findall('Affliction'))
                
                # Wallet
                wallet_elem = ccd.find('Wallet')
                if wallet_elem is not None:
                    balance = wallet_elem.get('balance', '0')
                    char_info['wallet_balance'] = int(balance) if balance.isdigit() else 0
                
                detailed_characters.append(char_info)
            
            result['characters'] = detailed_characters
            
        except Exception as e:
            print(f"Warning: Could not parse {char_xml_path}: {e}")
    
    return result
```

---

## Error Handling

### Common Issues and Solutions

1. **Invalid gzip streams**:
   - Some `1f 8b` patterns have invalid compression methods (not 0x08)
   - Always check `level0_data[i+2] == 0x08` before decompressing
   - Skip invalid positions silently

2. **XML parsing errors**:
   - Some streams may be corrupted or truncated
   - Validate XML before parsing with ET.fromstring()
   - Check for `<` and `>` characters first

3. **Encoding issues**:
   - Main XML is UTF-8 encoded
   - Header filename is UTF-16 LE
   - Handle decode errors gracefully

4. **Multiple valid streams**:
   - A save file may contain multiple valid Submarine XML streams
   - Choose the one with most characters (most complete state)
   - This handles both original and copy files correctly

5. **No CharacterData.xml**:
   - Not all save files have separate CharacterData.xml (only originals)
   - The extraction method still works, just with less detail from Submarine XML
   - Copy/played saves use only the embedded data in Submarine XML

---

## File Size Considerations

Save file sizes vary significantly:

| Original Size | Level 0 Size | Valid Gzip Streams |
|---------------|--------------|-------------------|
| ~95-120 KB | ~800-1,000 KB | Variable (2-6) |
| ~177 KB | ~370 KB | Variable |
| ~279 KB | ~516 KB | 5+ streams |
| ~299 KB | ~1,331 KB | 5+ streams |

The level 0 decompressed size is typically **5-10× larger** than the original file due to efficient gzip compression.

---

## Summary

| Aspect | Key Information |
|--------|-----------------|
| Header Size | Fixed at ~28 bytes (based on filename) |
| Valid Gzip Streams | Must have method = 0x08 (deflate) |
| Submarine XML Location | Varies; must search all valid streams |
| Best Stream Selection | Choose stream with most characters (most complete state) |

**The generic search approach works because:**
1. We check for `1f 8b 08` header (valid gzip)
2. We decompress each potential stream
3. We select the one with the most characters (most complete game state)

This handles both original and copy/played files correctly without needing to detect which type they are.
