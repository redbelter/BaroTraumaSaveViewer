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
        print('Root tag:', root.tag)
        print('Root name:', root.get('name'))
        print('Root type:', root.get('type'))
        print('Children:', [c.tag for c in root[:10]])
        
        # Look for campaigns/missions
        campaigns = list(root.findall('.//campaign'))
        print('\nCampaigns:', len(campaigns))
        if campaigns:
            c = campaigns[0]
            print('Campaign children:', [ch.tag for ch in c[:5]])
        
        # Look for missions
        missions = list(root.findall('.//mission'))
        print('Missions:', len(missions))
        
        # Look for locations
        locations = list(root.findall('.//map/location'))
        print('Locations in map:', len(locations))
        
        # Look for characters
        characters = list(root.findall('.//Character'))
        print('Characters:', len(characters))
        
        # Check campaignsettings
        cs = root.find('.//campaignsettings')
        if cs is not None:
            print('\ncampaignsettings:', dict(cs.attrib))
        
        # Check MultiPlayerCampaign
        mpc = root.find('.//MultiPlayerCampaign')
        if mpc is not None:
            print('\nMultiPlayerCampaign found')
            print('Children:', [ch.tag for ch in mpc])
