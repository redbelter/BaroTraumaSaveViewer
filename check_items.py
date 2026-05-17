# Check actual item identifiers and other data details
import gzip, io, pathlib, xml.etree.ElementTree as ET

path = pathlib.Path("data/samples/grav.save")
data = path.read_bytes()
buf = io.BytesIO(data)
with gzip.GzipFile(fileobj=buf) as gz:
    level0 = gz.read()

# Get gamesession.xml bytes
i = 0
gs_bytes = None
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
        gs_bytes = content
        break

text = gs_bytes.decode("utf-8", errors="replace").replace("\ufeff", "")
root = ET.fromstring(text)

# Check ALL Item elements - they may be nested deep
items = root.findall(".//Item")
print(f"Total Item elements: {len(items)}")
print("\nFirst 25 items:")
for idx, item in enumerate(items[:25]):
    ident = item.get("identifier", "MISSING")
    tags = item.get("Tags", "")
    cond = item.get("conditionpercentage", "")
    rect = item.get("rect", "")
    parent = item.get("parentid", "")
    parent_elem = item.find("parent")
    parent_name = parent_elem.get("name") if parent_elem is not None else "NONE"
    print(f"  [{idx}] id={item.get('ID','?')} ident={ident} tags={tags[:30]} cond={cond} parent={parent_name[:30]}")

print(f"\n...\nTotal: {len(items)} items")

# Check if there are more
if len(items) > 25:
    print(f"Items 25-50:")
    for idx, item in enumerate(items[25:50]):
        ident = item.get("identifier", "MISSING")
        tags = item.get("Tags", "")
        cond = item.get("conditionpercentage", "")
        print(f"  [{idx+25}] id={item.get('ID','?')} ident={ident} tags={tags[:30]} cond={cond}")

if len(items) > 50:
    print(f"\nItems 50-100:")
    for idx, item in enumerate(items[50:100]):
        ident = item.get("identifier", "MISSING")
        print(f"  [{idx+50}] id={item.get('ID','?')} ident={ident}")

# Also check if there are any Item elements with no identifier
no_ident = [it for it in items if not it.get("identifier")]
if no_ident:
    print(f"\nItems with NO identifier: {len(no_ident)}")
    for it in no_ident[:5]:
        print(f"  tag={it.tag} attribs={it.attrib}")

# Check all non-underscore identifiers
underscoreless = [it for it in items if "_" not in it.get("identifier", "")]
print(f"\nItems WITHOUT underscore in identifier: {len(underscoreless)}")
if underscoreless:
    for it in underscoreless[:10]:
        print(f"  ident={it.get('identifier')} id={it.get('ID')}")

# Check Character children with nested Item tags
chars = root.findall(".//Character")
print(f"\nCharacters: {len(chars)}")
for c in chars[:3]:
    inv = c.find(".//inventory")
    if inv is not None:
        inv_items = inv.findall(".//Item")
        print(f"  {c.get('name')} has {len(inv_items)} inventory items")
        for it in inv_items[:5]:
            print(f"    ident={it.get('identifier')}, id={it.get('ID')}")

# Check Submarine XML for structures
for name, clen, dlen, ftype in [(None, None, None, None)]:
    pass

# Re-extract and check submarine XML files for structures/items/gaps
print("\n=== Checking .sub files ===")
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
    
    if name.endswith(".sub"):
        # Try decompressing
        try:
            buf2 = io.BytesIO(content)
            with gzip.GzipFile(fileobj=buf2) as gz2:
                sub_xml = gz2.read().decode("utf-8", errors="replace")
            
            sub_root = ET.fromstring(sub_xml)
            hulls = sub_root.findall(".//Hull")
            structs = sub_root.findall(".//Structure")
            gaps = sub_root.findall(".//Gap")
            sub_items = sub_root.findall(".//Item")
            noitems = sub_root.get("noitems", "false")
            
            print(f"\n{name}:")
            print(f"  hulls: {len(hulls)}, structures: {len(structs)}, gaps: {len(gaps)}, items: {len(sub_items)}")
            print(f"  noitems={noitems}")
            print(f"  attributes: {dict(sub_root.attrib)}")
            
            # Check if sub has actual hull/structure/item children
            print(f"  top-level children: {[e.tag for e in sub_root]}")
            
            # Parse hulls
            for h in hulls[:3]:
                print(f"    hull: name={h.get('name')}, id={h.get('ID')}, hp={h.get('healthpercentage')}, integrity={h.get('integrity')}")
            
            # Parse structures
            for s in structs[:3]:
                rect = s.get("rect", "")
                size = ""
                if "size=" in rect:
                    import re
                    m = re.search(r'size="([^"]*)"', rect)
                    if m: size = m.group(1)
                print(f"    struct: name={s.get('name')}, id={s.get('ID')}, type={s.get('type')}, size={size}")
            
            # Parse items in sub
            if not noitems.lower() == "true":
                for it in sub_items[:5]:
                    ident = it.get("identifier", "")
                    itype = ident.split("_")[1].lower() if "_" in ident else "custom"
                    print(f"    item: id={it.get('ID')}, ident={ident} (type={itype}), cond={it.get('conditionpercentage')}")
                    
        except Exception as e:
            print(f"\n{name}: error parsing - {e}")
