# data bug fix
import gzip, io, pathlib, xml.etree.ElementTree as ET

path = pathlib.Path("data/samples/grav.save")
data = path.read_bytes()
buf = io.BytesIO(data)
with gzip.GzipFile(fileobj=buf) as gz:
    level0 = gz.read()

# Find gamesession.xml
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

# Check all top-level children of Gamesession
print("Gamesession top-level children:")
for c in root:
    print(f"  tag={c.tag} attribs={dict(c.attrib)}")
    if c.tag == "Hull":
        print(f"    id={c.get('ID')} healthpct={c.get('healthpercentage')} integrity={c.get('integrity')}")

# Check all Hull elements anywhere in the tree
all_hulls = root.findall(".//Hull")
print(f"\nAll Hull elements in tree: {len(all_hulls)}")
for h in all_hulls[:3]:
    print(f"  tag={h.tag} attribs={dict(h.attrib)}")

# Check Character structure in detail
chars = root.findall(".//Character")
print(f"\nCharacters: {len(chars)}")
for c in chars[:1]:
    print(f"  name={c.get('name')}")
    for child in c:
        print(f"    child tag={child.tag} attribs={dict(child.attrib)}")
        if child.tag == "inventory":
            for inv_item in child.findall(".//Item"):
                print(f"      item ident={inv_item.get('identifier')} id={inv_item.get('ID')}")
        elif child.tag == "health":
            for aff in child.findall(".//Affliction"):
                print(f"      affliction ident={aff.get('identifier')} strength={aff.get('strength')}")
            limb_count = len(child.findall("LimbHealth"))
            print(f"      LimbHealth count: {limb_count}")

# Check if missions have destinationindex attribute
mpc = root.find(".//MultiPlayerCampaign")
missions = mpc.findall(".//mission") if mpc is not None else []
print(f"\nMissions: {len(missions)}")
print(f"Mission attribs on first 3:")
for m in missions[:3]:
    print(f"  {dict(m.attrib)}")

# Check locations - look at location attributes carefully
all_locs = root.findall(".//location")
print(f"\nAll locations: {len(all_locs)}")
if all_locs:
    print(f"First location attribs: {dict(all_locs[0].attrib)}")
    # Check if any have 'index' or 'id' attributes
    for loc in all_locs[:3]:
        print(f"  name={loc.get('name')}, id={loc.get('id')}, index={loc.get('index')}")

# Check Metadata campaign.location.id values
meta = root.find(".//Metadata")
if meta is not None:
    loc_id_vals = [d.get('value') for d in meta.findall(".//Data") if d.get('key') == 'campaign.location.id']
    print(f"\ncampaign.location.id from Metadata: {loc_id_vals[:10]}")

# Check what attributes Hull elements actually have
print("\n=== .sub file hull attributes ===")
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
    
    if name.endswith(".sub") and "Orca2" in name:
        try:
            buf2 = io.BytesIO(content)
            with gzip.GzipFile(fileobj=buf2) as gz2:
                sub_xml = gz2.read().decode("utf-8", errors="replace")
            sub_root = ET.fromstring(sub_xml)
            
            hulls = sub_root.findall(".//Hull")
            print(f"\nOrca2 Hulls: {len(hulls)}")
            for h in hulls[:3]:
                print(f"  attribs={dict(h.attrib)}")
            
            structs = sub_root.findall(".//Structure")
            print(f"\nOrca2 Structures: {len(structs)}")
            for s in structs[:3]:
                print(f"  attribs={dict(s.attrib)}")
            
            gaps = sub_root.findall(".//Gap")
            print(f"\nOrca2 Gaps: {len(gaps)}")
            for g in gaps[:3]:
                print(f"  attribs={dict(g.attrib)}")
            
            items = sub_root.findall(".//Item")
            print(f"\nOrca2 Items: {len(items)}")
            for it in items[:5]:
                print(f"  attribs={dict(it.attrib)}")
            break
        except Exception as e:
            print(f"Error: {e}")
            break
