from typing import List, Tuple
import datetime
import uuid

from .historic_aircraft_data import HistoricAircraftData
from .maritime_craft import MaritimeCraft
from .complex_geometry import ComplexGeometry
from .descriptions import Description
from .point_geometry import PointGeometry
from .monument_dated_types import MonumentDatedTypes
from .monument import Monument
from .historic_aircraft_model import HistoricAircraftModel
from .maritime_vessel import MaritimeVessel
from .monument_sources import MonumentSource
from .object_finds import ObjectFinds
from .related_monument_records import RelatedMonumentRecord
from .images import Image
from .related_events import RelatedEvent


def create_resource(
    resource_type: str, 
    resource_instance_id: uuid.UUID, 
    primary_reference_number: str, 
    heritage_asset_name: str, 
    descriptions: List[Description], 
    point_geometry: PointGeometry, 
    complex_geometry: ComplexGeometry, 
    last_updated: datetime.datetime, 
    monument_sources: List[MonumentSource] = None,
    object_finds: List[ObjectFinds] = None,
    monument_dated_types: List[MonumentDatedTypes] = None,
    maritime_craft: List[MaritimeCraft] = None,
    historic_aircraft: List[HistoricAircraftData] = None,
    related_monument_records: List[RelatedMonumentRecord] = None,
    images: List[Image] = None,
    other_statuses: List[str] = None,
    related_events: List[RelatedEvent] = None,
    protected_statuses: List[str] = None
):
    if resource_type == "Monument":
        return Monument(
            resource_instance_id=resource_instance_id,
            primary_reference_number=primary_reference_number,
            heritage_asset_name=heritage_asset_name,
            descriptions=descriptions,
            monument_dated_types=monument_dated_types,
            point_geometry=point_geometry,
            complex_geometry=complex_geometry,
            monument_sources=monument_sources,
            object_finds=object_finds,
            maritime_craft=maritime_craft,
            historic_aircraft=historic_aircraft,
            related_monument_records=related_monument_records,
            images=images,
            other_statuses=other_statuses,
            related_events=related_events,
            protected_statuses=protected_statuses,
            last_updated=last_updated)
    elif resource_type == "Historic Aircraft":
        return HistoricAircraftModel(
            resource_instance_id=resource_instance_id,
            primary_reference_number=primary_reference_number,
            heritage_asset_name=heritage_asset_name,
            descriptions=descriptions,
            point_geometry=point_geometry,
            complex_geometry=complex_geometry,
            last_updated=last_updated)
    elif resource_type == "Maritime Vessel":
        return MaritimeVessel(
            resource_instance_id=resource_instance_id,
            primary_reference_number=primary_reference_number,
            heritage_asset_name=heritage_asset_name,
            descriptions=descriptions,
            point_geometry=point_geometry,
            complex_geometry=complex_geometry,
            last_updated=last_updated)
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")
