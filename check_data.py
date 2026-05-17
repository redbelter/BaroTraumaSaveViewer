# Check what the grav.save file actually contains
import gzip, io, pathlib, xml.etree.ElementTree as ET

path = pathlib.Path("data/samples/grav.save")
data = path.read_bytes()
print(f"File size: {len(data)} bytes")

buf = io.BytesIO(data)
with gzip.GzipFile(fileobj=buf) as gz:
    level0 = gz.read()
print(f"Level 0 decompressed: {len(level0)} bytes")

# Extract raw files
i = 0
raw_files = []
while i + 4 <= len(level0):
    name_len = int.from_bytes(level0[i:i+4], "little")
    if name_len < 0 or name_len > 10000 or i + name_len * 2 > len(level0):
        break
    i += 4
    name = level0[i:i+name_len*2].decode("utf-16-le", errors="replace")
    i += name_len * 2
    if i + 4 > len(level0):
        break
    content_len = int.from_bytes(level0[i:i+4], "little")
    if content_len < 0 or content_len > 100_000_000 or i + 4 + content_len > len(level0):
        break
    i += 4
    content = level0[i:i+content_len]
    i += content_len
    
    # Try decompressing
    decompressed = None
    try:
        buf2 = io.BytesIO(content)
        with gzip.GzipFile(fileobj=buf2) as gz2:
            decompressed = gz2.read()
        if decompressed:
            ftype = "nested_gzip"
        else:
            ftype = "empty"
    except:
        decompressed = content
        ftype = "raw_text"
    
    raw_files.append((name, len(content), len(decompressed), ftype))
    print(f"File: {name} | compressed: {len(content)} | decompressed: {len(decompressed)} | type: {ftype}")

print("\n\n=== Now parsing gamesession.xml ===\n")

# Find and parse gamesession.xml
gamesession_bytes = None
for name, clen, dlen, ftype in raw_files:
    if "gamesession" in name.lower():
        # Get the raw content from the raw_files extraction
        break

# Re-read gamesession.xml properly
i = 0
while i + 4 <= len(level0):
    name_len = int.from_bytes(level0[i:i+4], "little")
    if name_len < 0 or name_len > 10000 or i + name_len * 2 > len(level0):
        break
    i += 4
    name = level0[i:i+name_len*2].decode("utf-16-le", errors="replace")
    i += name_len * 2
    if i + 4 > len(level0):
        break
    content_len = int.from_bytes(level0[i:i+4], "little")
    if content_len < 0 or content_len > 100_000_000 or i + 4 + content_len > len(level0):
        break
    i += 4
    content = level0[i:i+content_len]
    i += content_len
    
    if "gamesession" in name.lower():
        gamesession_bytes = content
        text = content.decode("utf-8", errors="replace").replace("\ufeff", "")
        print(f"gamesession.xml: {len(text)} chars\n")
        
        root = ET.fromstring(text)
        
        # === Characters ===
        chars = root.findall(".//Character")
        print(f"Characters: {len(chars)}")
        for c in chars[:5]:
            j = c.find(".//job")
            job_name = j.get("name") if j is not None else "???"
            print(f"  name={c.get('name')}, job={job_name}, id={c.get('id')}, condition={c.get('conditionpercentage')}")
        if len(chars) > 5:
            print(f"  ... and {len(chars)-5} more")
        
        # === Items ===
        items = root.findall(".//Item")
        print(f"\nItems: {len(items)}")
        item_types = {}
        for item in items:
            ident = item.get("identifier", "unknown")
            t = ident.split("_")[1].lower() if "_" in ident else "custom"
            item_types[t] = item_types.get(t, 0) + 1
        for t, c in sorted(item_types.items()):
            print(f"  {t}: {c}")
        
        # === Hulls ===
        hulls = root.findall(".//Hull")
        print(f"\nHulls: {len(hulls)}")
        for h in hulls[:5]:
            print(f"  name={h.get('name')}, id={h.get('ID')}, healthpct={h.get('healthpercentage')}, integrity={h.get('integrity')}")
        
        # === Structures ===
        structs = root.findall(".//Structure")
        print(f"\nStructures: {len(structs)}")
        for s in structs[:3]:
            print(f"  name={s.get('name')}, id={s.get('ID')}, type={s.get('type')}, rect={s.get('rect')[:80]}")
        
        # === Gaps ===
        gaps = root.findall(".//Gap")
        print(f"\nGaps: {len(gaps)}")
        for g in gaps[:3]:
            print(f"  id={g.get('ID')}, rect={g.get('rect')[:80]}")
        
        # === Missions ===
        mpc = root.find(".//MultiPlayerCampaign")
        if mpc is not None:
            missions = mpc.findall(".//mission")
            print(f"\nMissions: {len(missions)}")
            for m in missions:
                print(f"  prefab={m.get('prefabid')}, selected={m.get('selected')}, dest_idx={m.get('destinationindex')}")
        
        # === Locations ===
        locations = root.findall(".//location")
        print(f"\nLocations (flat): {len(locations)}")
        for loc in locations[:5]:
            print(f"  name={loc.get('name')}, type={loc.get('type')}, biome={loc.get('biome')}")
        
        maps = root.findall(".//map")
        print(f"\nMaps: {len(maps)}")
        for map_elem in maps:
            map_locs = map_elem.findall(".//location")
            print(f"  map locations: {len(map_locs)}")
            for ml in map_locs[:3]:
                print(f"    name={ml.get('name')}, type={ml.get('type')}, biome={ml.get('biome')}")
        
        # === Submarine ===
        print(f"\nSubmarine tag: {root.get('submarine')}")
        
        # === Campaign Settings ===
        cs = root.find(".//campaignsettings")
        if cs is not None:
            print(f"\nCampaign Settings:")
            for k, v in cs.attrib.items():
                print(f"  {k}={v}")
        
        # === Metadata ===
        meta = root.find(".//Metadata")
        if meta is not None:
            data_items = meta.findall(".//Data")
            print(f"\nMetadata entries: {len(data_items)}")
            for d in data_items[:5]:
                print(f"  key={d.get('key')}, value={d.get('value')}")
            if len(data_items) > 5:
                print(f"  ... and {len(data_items)-5} more")
        
        # Check for character data files
        char_data_files = []
        for name, clen, dlen, ftype in raw_files:
            if "characterdata" in name.lower() or "character" in name.lower():
                char_data_files.append((name, clen, dlen, ftype))
        if char_data_files:
            print(f"\nCharacter data files found: {len(char_data_files)}")
            for cdf in char_data_files:
                print(f"  {cdf[0]} | compressed: {cdf[1]} | decompressed: {cdf[2]} | type: {cdf[3]}")
        
        break
