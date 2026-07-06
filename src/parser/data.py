"""Dataclasses for Barotrauma save file objects."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SubmarineInfo:
    name: str = "Unknown"
    sub_type: str = "Unknown"
    class_: str = "Unknown"
    tier: str = "Unknown"
    game_version: str = "Unknown"
    dimensions: str = "Unknown"
    cargo_capacity: str = "Unknown"
    price: str = "Unknown"
    tags: str = "Unknown"


@dataclass
class Character:
    id: str
    name: str
    job: str
    condition: str = "Unknown"
    position: str = ""
    status: str = "Unknown"  # "Living", "Campaign", "In Duffelbag", "Unknown"
    permanently_dead: bool = False
    destination_index: Optional[int] = None
    tags: str = ""
    parent_id: str = ""


@dataclass
class Hull:
    id: str
    name: str
    health_pct: float
    integrity: float
    damage: float


@dataclass
class Structure:
    id: str
    name: str
    struct_type: str
    position: str
    size: str


@dataclass
class Gap:
    id: str
    position: str
    size: str


@dataclass
class Item:
    id: str
    identifier: str
    item_type: str
    position: str = ""
    condition_pct: float = 100.0
    tags: str = ""
    parent_id: str = ""


@dataclass
class Location:
    name: str
    location_type: str
    biome: str = "Unknown"
    position: str = "Unknown"
    index: Optional[int] = None


@dataclass
class Mission:
    prefab_id: str
    location: str
    mission_type: str = "Unknown"
    destination_index: Optional[int] = None
    origin_index: Optional[int] = None
    times_attempted: int = 0
    selected: bool = False


@dataclass
class CampaignSettings:
    max_mission_count: Optional[int] = None
    max_mission_attempts: Optional[int] = None
    # Extra campaign fields captured as-is
    extra: dict = field(default_factory=dict)


@dataclass
class SaveFile:
    """All parsed data from a single save file."""

    path: Path
    original_size: int = 0
    decompressed_size: int = 0
    submarine: SubmarineInfo = field(default_factory=SubmarineInfo)
    characters: list[Character] = field(default_factory=list)
    hulls: list[Hull] = field(default_factory=list)
    structures: list[Structure] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    missions: list[Mission] = field(default_factory=list)
    campaign_settings: Optional[CampaignSettings] = None
    raw_xml: Optional[str] = None
    sub_position: Optional[tuple[float, float]] = None


def item_type_from_identifier(identifier: str) -> str:
    """Derive item type from its identifier.

    Barotrauma identifier format is <category>_<type>[_<subcategory>], e.g.:
    - gun_shotgun -> shotgun
    - duffelbag_container -> container

    For single-word identifiers (no underscore), the identifier IS the type:
    - idcard -> idcard
    - weldingtool -> weldingtool
    """
    if "_" in identifier:
        return identifier.split("_")[1].lower()
    return identifier.lower()
