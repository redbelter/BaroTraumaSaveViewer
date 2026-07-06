"""XML -> dataclass conversion."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .data import (
    CampaignSettings,
    Character,
    Gap,
    Hull,
    Item,
    Location,
    Mission,
    SaveFile,
    Structure,
    SubmarineInfo,
    item_type_from_identifier,
)


def _float_attr(elem: ET.Element, attr: str, default: float = 100.0) -> float:
    try:
        return float(elem.get(attr, default))
    except (ValueError, TypeError):
        return default


def _int_attr(elem: ET.Element, attr: str, default: int = 0) -> int:
    try:
        return int(elem.get(attr, default))
    except (ValueError, TypeError):
        return default


def _parse_position(text: str) -> tuple[float, float] | None:
    """Parse 'x,y' or 'x, y' into float tuple."""
    try:
        parts = text.strip().replace(" ", "").split(",")
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except (ValueError, AttributeError):
        pass
    return None


def parse_submarine(xml_str: str) -> SubmarineInfo:
    root = ET.fromstring(xml_str)
    return SubmarineInfo(
        name=root.get("name", "Unknown"),
        sub_type=root.get("type", "Unknown"),
        class_=root.get("class", "Unknown"),
        tier=root.get("tier", "Unknown"),
        game_version=root.get("gameversion", "Unknown"),
        dimensions=root.get("dimensions", "Unknown"),
        cargo_capacity=root.get("cargocapacity", "Unknown"),
        price=root.get("price", "Unknown"),
        tags=root.get("Tags", "Unknown"),
    )


def parse_characters_from_xml(xml_str: str, status: str = "In Duffelbag") -> list[Character]:
    """Parse characters from an XML string, extracting health from the <health> subtree."""
    chars: list[Character] = []
    root = ET.fromstring(xml_str)
    
    for elem in root.findall(".//Character"):
        # Get basic character attributes
        char_id = elem.get("id", "0")
        name = elem.get("name", "Unknown")
        job = elem.get("job", "Unknown")
        
        # Extract health percentage from <health> subtree if present
        condition = "100.00%"
        health_elem = elem.find("health")
        if health_elem is not None:
            # Calculate average limb health
            limb_count = len(health_elem.findall("LimbHealth"))
            if limb_count > 0:
                total = 0.0
                for limb in health_elem.findall("LimbHealth"):
                    total += float(limb.get("value", limb.get("value", "100")))
                condition = f"{total / limb_count:.2f}%"
        
        position = elem.get("rect", "")
        
        chars.append(Character(
            id=char_id,
            name=name,
            job=job,
            condition=condition,
            position=position,
            status=status,
        ))
    return chars


def parse_hulls_from_xml(xml_str: str) -> list[Hull]:
    """Parse hulls from a Submarine XML. Handles both template (.sub) and in-game formats.
    
    Template hulls: <Hull ID="152" /> (bare, no attributes)
    In-game hulls: <Hull ID="152" healthpercentage="80.5" integrity="95.0" />
    """
    hulls: list[Hull] = []
    root = ET.fromstring(xml_str)
    
    for h in root.findall(".//Hull"):
        hull_id = h.get("ID", "Unknown")
        # Template hulls have no attributes; in-game hulls have healthpercentage and integrity
        health_pct = _float_attr(h, "healthpercentage", 100.0)
        integrity = _float_attr(h, "integrity", 100.0)
        # If no attributes exist, use the defaults (100% healthy)
        has_data = h.attrib and len(h.attrib) > 1  # ID is always there, so check for >1 attrs
        if not has_data:
            health_pct = 100.0
            integrity = 100.0
        
        hulls.append(Hull(
            id=hull_id,
            name=f"Hull-{hull_id}",  # Template hulls don't have names
            health_pct=health_pct,
            integrity=integrity,
            damage=100.0 - integrity,
        ))
    return hulls


def parse_structures_from_xml(xml_str: str) -> list[Structure]:
    """Parse structures from a Submarine XML.
    
    Handles both template (.sub) format (uses 'name' attr) and in-game format (uses 'rect' with size).
    """
    structures: list[Structure] = []
    root = ET.fromstring(xml_str)
    
    for s in root.findall(".//Structure"):
        struct_id = s.get("ID", "Unknown")
        # Template structures use 'name' attribute directly
        name = s.get("name", f"Structure-{struct_id}")
        struct_type = s.get("type", "custom")
        
        rect = s.get("rect", "")
        size = "Unknown"
        if "size=" in rect:
            m = re.search(r'size="([^"]*)"', rect)
            if m:
                size = m.group(1)
        
        structures.append(Structure(
            id=struct_id,
            name=name,
            struct_type=struct_type,
            position=rect,
            size=size,
        ))
    return structures


def parse_gaps_from_xml(xml_str: str) -> list[Gap]:
    """Parse gaps from a Submarine XML.
    
    Gaps in .sub files use 'name' attribute, not 'rect'.
    """
    gaps: list[Gap] = []
    root = ET.fromstring(xml_str)
    
    for g in root.findall(".//Gap"):
        gap_id = g.get("ID", "Unknown")
        rect = g.get("rect", "")
        size = "Unknown"
        if "size=" in rect:
            m = re.search(r'size="([^"]*)"', rect)
            if m:
                size = m.group(1)
        
        gaps.append(Gap(
            id=gap_id,
            position=rect,
            size=size,
        ))
    return gaps


def parse_items_from_xml(xml_str: str) -> list[Item]:
    items: list[Item] = []
    root = ET.fromstring(xml_str)
    
    for elem in root.findall(".//Item"):
        identifier = elem.get("identifier", "unknown")
        items.append(Item(
            id=elem.get("ID", "Unknown"),
            identifier=identifier,
            item_type=item_type_from_identifier(identifier),
            position=elem.get("rect", ""),
            condition_pct=_float_attr(elem, "conditionpercentage", 100.0),
            tags=elem.get("Tags", ""),
            parent_id=elem.get("parentid", ""),
        ))
    return items


def parse_campaign(xml_str: str, sf: SaveFile) -> None:
    """Parse campaign data from gamesession.xml.
    
    Handles the actual structure:
    - Missions are in MultiPlayerCampaign/metadata/Mission elements
    - Campaign metadata uses <Metadata><Data key="campaign.location.*" value="..." /></Data>
    - Characters have health info in <health> subtree
    - Locations are in <map><location> elements
    """
    root = ET.fromstring(xml_str)

    # Campaign settings
    campaign = root.find(".//campaignsettings")
    if campaign is not None:
        sf.campaign_settings = CampaignSettings(
            max_mission_count=_int_attr(campaign, "MaxMissionCount"),
            max_mission_attempts=_int_attr(campaign, "MaxMissionAttempts"),
        )
        for k, v in campaign.attrib.items():
            if k not in ("MaxMissionCount", "MaxMissionAttempts"):
                sf.campaign_settings.extra[k] = v
        # Sub position: campaignsettings text, or position attr, or from campaign.location.id in metadata
        sub_txt = campaign.text or campaign.get("position")
        if sub_txt and sub_txt.strip():
            coords = _parse_position(sub_txt.strip())
            if coords:
                sf.sub_position = coords

    # Locations from map
    map_elem = root.find(".//map")
    if map_elem is not None:
        for idx, loc in enumerate(map_elem.findall(".//location")):
            sf.locations.append(Location(
                name=loc.get("name", "Unknown"),
                location_type=loc.get("type", "Unknown"),
                biome=loc.get("biome", "Unknown"),
                position=loc.get("position", "Unknown"),
                index=idx,
            ))

    # Fallback: locations anywhere
    if not sf.locations:
        for loc in root.findall(".//location"):
            sf.locations.append(Location(
                name=loc.get("name", "Unknown"),
                location_type=loc.get("type", "Unknown"),
                biome=loc.get("biome", "Unknown"),
                position=loc.get("position", "Unknown"),
            ))

    # Campaign characters (extract from both root level and any nested)
    for char in root.findall(".//Character"):
        permanently_dead = (
            char.get("permanentlydead", "false").lower() == "true"
        )
        
        # Extract condition from <health> subtree
        condition = "100.00%"
        health_elem = char.find("health")
        if health_elem is not None:
            limb_count = len(health_elem.findall("LimbHealth"))
            if limb_count > 0:
                total = 0.0
                for limb in health_elem.findall("LimbHealth"):
                    total += float(limb.get("value", "100"))
                condition = f"{total / limb_count:.2f}%"
        
        sf.characters.append(Character(
            id=char.get("id", "0"),
            name=char.get("name", "Unknown"),
            job=char.get("job", "Unknown"),
            condition=condition,
            position=char.get("rect", ""),
            status="Campaign" if not permanently_dead else "Dead",
            permanently_dead=permanently_dead,
            destination_index=(
                _int_attr(char, "destinationindex")
                if char.get("destinationindex")
                else None
            ),
        ))

    # Missions - in Barotrauma, missions are stored as <Mission> elements within <Metadata>
    # Each mission has metadata entries like:
    #   <Data key="mission.{prefab_id}.destinationindex" value="{idx}" type="System.Int32" />
    #   <Data key="mission.{prefab_id}.selected" value="true" type="System.Boolean" />
    #   <Data key="mission.{prefab_id}.timesattempted" value="3" type="System.Int32" />
    mpc = root.find('.//MultiPlayerCampaign')
    if mpc is not None:
        metadata = mpc.find('Metadata')
        
        # Extract all campaign metadata for mission data
        mission_data: dict[str, dict] = {}
        mission_prefabs: list[str] = []

        if metadata is not None:
            for data_elem in metadata.findall(".//Data"):
                key = data_elem.get("key", "")
                value = data_elem.get("value", "")
                # Sub current location: campaign.location.id = location_index
                if key == "campaign.location.id" and sf.sub_position is None:
                    try:
                        loc_idx = int(value)
                        for loc in sf.locations:
                            if loc.index == loc_idx:
                                parsed = _parse_position(loc.position)
                                if parsed:
                                    sf.sub_position = parsed
                                break
                    except (ValueError, TypeError):
                        pass
                # Mission metadata keys look like "mission.{prefab_id}.{field}"
                if key.startswith("mission."):
                    parts = key.split(".", 2)
                    if len(parts) >= 3:
                        prefab_id = parts[1]
                        field_name = parts[2]
                        if prefab_id not in mission_data:
                            mission_data[prefab_id] = {}
                            mission_prefabs.append(prefab_id)
                        mission_data[prefab_id][field_name] = value
        
        # Map destination indices to locations
        loc_by_index = {loc.index: loc for loc in sf.locations}
        
        for prefab_id in mission_prefabs:
            mdata = mission_data.get(prefab_id, {})
            
            # Parse destination index
            dest_idx_str = mdata.get("destinationindex")
            if dest_idx_str is not None:
                try:
                    dest_idx = int(dest_idx_str)
                except (ValueError, TypeError):
                    dest_idx = None
            else:
                dest_idx = None
            
            # Parse mission origin from metadata
            origin_str = mdata.get("origin")
            if origin_str is not None:
                try:
                    origin_idx = int(origin_str)
                except (ValueError, TypeError):
                    origin_idx = None
            else:
                origin_idx = None
    
            # Find location name from destination index
            if dest_idx is not None and dest_idx in loc_by_index:
                loc = loc_by_index[dest_idx]
                loc_name = loc.name
                mission_type = loc.location_type
            else:
                loc_name = 'Unknown'
                mission_type = 'Unknown'
    
            # Parse selected
            selected_str = mdata.get("selected", "false")
            selected = selected_str.lower() == "true" if selected_str else False
    
            # Parse times attempted
            try:
                times_attempted = int(mdata.get("timesattempted", "0"))
            except (ValueError, TypeError):
                times_attempted = 0
    
            sf.missions.append(Mission(
                prefab_id=prefab_id,
                location=loc_name,
                mission_type=mission_type,
                destination_index=dest_idx,
                origin_index=origin_idx,
                times_attempted=times_attempted,
                selected=selected,
            ))

    # Also check for mission elements directly (legacy format)
    if not sf.missions:
        if mpc is not None:
            all_missions = mpc.findall('.//mission')
            if all_missions:
                loc_by_name = {loc.name: loc for loc in sf.locations}
                for mission_xml in all_missions:
                    dest_idx = _int_attr(mission_xml, 'destinationindex')
                    if dest_idx is not None and 0 <= dest_idx < len(sf.locations):
                        loc = sf.locations[dest_idx]
                        loc_name = loc.name
                        mission_type = loc.location_type
                    else:
                        loc_name = 'Unknown'
                        mission_type = 'Unknown'
                    
                    sf.missions.append(Mission(
                        prefab_id=mission_xml.get('prefabid', 'Unknown'),
                        location=loc_name,
                        mission_type=mission_type,
                        destination_index=dest_idx,
                        origin_index=_int_attr(mission_xml, 'origin'),
                        times_attempted=_int_attr(mission_xml, 'TimesAttempted'),
                        selected=(
                            mission_xml.get('selected', 'false').lower() == 'true'
                        ),
                    ))


def parse_character_data(xml_src: str) -> list[Character]:
    """Parse character data from CharacterData.xml filepath or raw XML string."""
    try:
        if xml_src.strip().startswith("<"):
            root = ET.fromstring(xml_src)
        else:
            root = ET.parse(xml_src).getroot()
        chars: list[Character] = []
        for campaign in root.findall(".//CharacterCampaignData"):
            char_elem = campaign.find(".//Character")
            if char_elem is None:
                continue
            permanently_dead = (
                char_elem.get("permanentlydead", "false").lower() == "true"
            )
            if permanently_dead:
                continue
            job_elem = char_elem.find(".//job")
            job_name = job_elem.get("name", "Unknown") if job_elem is not None else "Unknown"
            chars.append(Character(
                id=campaign.get("name", "Unknown"),
                name=char_elem.get("name", "Unknown"),
                job=job_name,
                condition="Alive",
                position="Living Crew",
                status="Living",
                permanently_dead=False,
            ))
        return chars
    except Exception as e:
        print(f"Warning: Could not parse character data: {e}")
        return []
