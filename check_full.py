import gzip, io, pathlib, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

path = Path("data/samples/grav.save")
data = path.read_bytes()
buf = io.BytesIO(data)
with gzip.GzipFile(fileobj=buf) as gz:
    level0 = gz.read()

i = 0
while i + 4 <= len(level0):
    nl = int.from_bytes(level0[i:i+4], 'little')
    if nl < 0 or nl > 10000 or i + nl * 2 > len(level0): break
    i += 4
    nm = level0[i:i+nl*2].decode('utf-16-le', errors='replace')
    i += nl * 2
    if i + 4 > len(level0): break
    cl = int.from_bytes(level0[i:i+4], 'little')
    if cl < 0 or cl > 100000000 or i + 4 + cl > len(level0): break
    i += 4
    content = level0[i:i+cl]
    i += cl
    if 'character' in nm.lower():
        print(f"{nm}: {len(content)} bytes")
        text = content.decode('utf-8', errors='ignore')
        print(f"  first 500: {text[:500]}")
    if 'gamesession' in nm.lower():
        text = content.decode('utf-8', errors='ignore')
        # Remove BOM
        if text.startswith('\ufeff'):
            text = text[1:]
        print(f"\ngamesession.xml: {len(text)} chars")
        # Show first 3000
        print(text[:3000])
        # Find key elements
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        print(f"\n=== Top-level children of Gamesession: ===")
        for c in root:
            print(f"  tag={c.tag} attribs={dict(c.attrib)}")
        print(f"\n=== All Character elements: ===")
        chars = root.findall(".//Character")
        print(f"Count: {len(chars)}")
        for c in chars[:3]:
            print(f"  name={c.get('name')}, job={c.get('job')}, id={c.get('id')}")
            # Show health subtree
            health = c.find("health")
            if health is not None:
                limb_count = len(health.findall("LimbHealth"))
                aff = len(health.findall(".//Affliction"))
                print(f"    health: {limb_count} limbs, {aff} afflictions")
        print(f"\n=== All hull elements in tree: ===")
        all_hulls = root.findall(".//Hull")
        print(f"Count: {len(all_hulls)}")
        for h in all_hulls[:3]:
            print(f"  {dict(h.attrib)}")
        print(f"\n=== Locations: ===")
        locs = root.findall(".//location")
        print(f"Count: {len(locs)}")
        for loc in locs[:5]:
            print(f"  name={loc.get('name')}, type={loc.get('type')}, biome={loc.get('biome')}")
        print(f"\n=== Campaign settings: ===")
        cs = root.find(".//campaignsettings")
        if cs is not None:
            print(f"  {dict(cs.attrib)}")
        print(f"\n=== MultiPlayerCampaign/Metadata: ===")
        mpc = root.find(".//MultiPlayerCampaign")
        if mpc is not None:
            meta = mpc.find('Metadata')
            if meta is not None:
                mission_data = meta.findall(".//Data")
                print(f"  Data entries: {len(mission_data)}")
                # Show mission-related ones
                for d in mission_data[:20]:
                    k = d.get('key', '')
                    if 'mission' in k.lower() or 'campaign' in k.lower():
                        print(f"    {k} = {d.get('value')}")
            # Also check for missions as children
            missions = mpc.findall(".//mission")
            print(f"  mission elements: {len(missions)}")
            for m in missions[:5]:
                print(f"    {dict(m.attrib)}")
            # Check campaign.children
            children = mpc.findall(".//Character")
            print(f"\n  Campaign children: {len(children)}")
            for ch in children[:3]:
                print(f"    {dict(ch.attrib)}")
        print(f"\n=== Metadata (flat): ===")
        all_meta = root.findall(".//Metadata")
        print(f"Count: {len(all_meta)}")
        for m in all_meta:
            datas = m.findall(".//Data")
            print(f"  Metadata Data entries: {len(datas)}")
            for d in datas[:10]:
                print(f"    {d.get('key')} = {d.get('value')}")
