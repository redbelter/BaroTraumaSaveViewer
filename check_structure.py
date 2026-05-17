import gzip, io, pathlib, sys, xml.etree.ElementTree as ET
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
    i += content_len
    if 'gamesession' in nm.lower():
        # gamesession is raw text with UTF-8 BOM
        text = content.decode('utf-8', errors='ignore')
        if text.startswith('\ufeff'): text = text[1:]
        root = ET.fromstring(text)
        
        print(f"=== Top-level children of Gamesession ===")
        for c in root:
            print(f"  tag={c.tag} attribs={dict(c.attrib)}")
        
        # Check campaign settings
        cs = root.find('.//campaignsettings')
        print(f"\n=== campaignsettings ===")
        if cs is not None:
            print(f"  {dict(cs.attrib)}")
        else:
            # Maybe it's at top level
            cs2 = root.find('campaignsettings')
            if cs2 is not None:
                print(f"  found at root level: {dict(cs2.attrib)}")
        
        # Check characters - are they under MultiPlayerCampaign or direct?
        all_chars = root.findall('.//Character')
        print(f"\n=== All Character elements: {len(all_chars)} ===")
        for c in all_chars[:3]:
            print(f"  name={c.get('name')}, job={c.get('job')}, id={c.get('id')}, permanentlydead={c.get('permanentlydead')}")
            # Show health
            health = c.find('health')
            if health is not None:
                limbs = health.findall('LimbHealth')
                aff = health.findall('.//Affliction')
                print(f"    health: {len(limbs)} limbs, {len(aff)} afflictions")
        
        # Check locations
        all_locs = root.findall('.//location')
        print(f"\n=== All location elements: {len(all_locs)} ===")
        for loc in all_locs[:5]:
            print(f"  name={loc.get('name')}, type={loc.get('type')}, biome={loc.get('biome')}, index={loc.get('index')}, id={loc.get('id')}")
            if loc.tag == 'location':
                # Check for sub-elements
                for sub in loc:
                    print(f"    sub tag={sub.tag} attribs={dict(sub.attrib)}")
        
        # Check MultiPlayerCampaign
        mpc = root.find('.//MultiPlayerCampaign')
        print(f"\n=== MultiPlayerCampaign ===")
        if mpc is not None:
            print(f"  children tags: {[c.tag for c in mpc]}")
            missions = mpc.findall('.//mission')
            print(f"  mission elements: {len(missions)}")
            for m in missions[:5]:
                print(f"    {dict(m.attrib)}")
            campaigns = mpc.findall('.//campaign')
            print(f"  campaign elements: {len(campaigns)}")
            for camp in campaigns[:2]:
                print(f"    {dict(camp.attrib)}")
                for sub in camp:
                    print(f"      sub tag={sub.tag} attribs={dict(sub.attrib)}")
        else:
            print("  Not found")
        
        # Check Metadata
        all_meta = root.findall('.//Metadata')
        print(f"\n=== Metadata elements: {len(all_meta)} ===")
        for meta in all_meta:
            print(f"  tag={meta.tag} attribs={dict(meta.attrib)}")
            for d in meta.findall('.//Data')[:20]:
                k = d.get('key', '')
                if 'mission' in k.lower() or 'campaign' in k.lower():
                    print(f"    {k} = {d.get('value')}")
