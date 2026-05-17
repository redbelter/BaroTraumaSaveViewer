import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

save_path = Path('data/potato 2.save')
with open(save_path, 'rb') as f:
    data = f.read()

level0 = gzip.decompress(data)
i = 0
while i + 4 <= len(level0):
    name_len = int.from_bytes(level0[i:i+4], 'little')
    if name_len < 0 or name_len > 10000:
        break
    i += 4
    name = level0[i:i+name_len*2].decode('utf-16-le')
    i += name_len * 2
    content_len = int.from_bytes(level0[i:i+4], 'little')
    i += 4
    content = level0[i:i+content_len]
    i += content_len
    
    if 'gamesession' in name.lower():
        print('Found gamesession.xml (%d bytes)' % content_len)
        xml_str = content.decode('utf-8', errors='ignore')
        root = ET.fromstring(xml_str)
        
        mpc = root.find('.//MultiPlayerCampaign')
        if mpc is not None:
            map_elem = mpc.find('map')
            if map_elem is not None:
                locations = list(map_elem.findall('.//location'))
                print(f'Locations: {len(locations)}')
                for loc in locations[:5]:
                    print(f'  name={loc.get("name")} type={loc.get("type")} biome={loc.get("biome")}')
                    missions = list(loc.findall('.//missions/mission'))
                    print(f'    missions: {len(missions)}')
                    for m in missions[:2]:
                        print(f'      prefabid={m.get("prefabid")}')
            
            # Also check missions directly under MultiPlayerCampaign
            all_missions = list(mpc.findall('.//missions/mission'))
            print(f'\nAll missions under MP Campaign: {len(all_missions)}')
            if all_missions:
                print('First mission:', all_missions[0].attrib)
            
            # Check if missions are on map/location elements
            print(f'\nMap children: {[ch.tag for ch in map_elem]}')
