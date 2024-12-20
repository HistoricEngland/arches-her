from typing import List, Tuple
import datetime
import uuid

from .images import Image
from .historic_aircraft_data import HistoricAircraftData
from .maritime_craft import MaritimeCraft
from .base import Base
from .complex_geometry import ComplexGeometry
from .point_geometry import PointGeometry
from .descriptions import Description
from .monument_dated_types import MonumentDatedTypes
from .monument_sources import MonumentSource
from .object_finds import ObjectFinds
from .related_monument_records import RelatedMonumentRecord
from .related_events import RelatedEvent


class Monument(Base):
    def __init__(
        self, 
        resource_instance_id: uuid.UUID, 
        primary_reference_number: str, 
        heritage_asset_name: str, 
        descriptions: List[Description], 
        monument_dated_types: List[MonumentDatedTypes], 
        point_geometry: PointGeometry, 
        complex_geometry: ComplexGeometry, 
        monument_sources: List[MonumentSource],
        object_finds: List[ObjectFinds],
        maritime_craft: List[MaritimeCraft], 
        historic_aircraft: List[HistoricAircraftData],
        related_monument_records: List[RelatedMonumentRecord],
        images: List[Image],
        other_statuses: List[str],
        related_events: List[RelatedEvent],
        last_updated: datetime.datetime,
        protected_statuses = List[str]
    ):
        super().__init__(
            resource_instance_id=resource_instance_id, 
            primary_reference_number=primary_reference_number,
            heritage_asset_name=heritage_asset_name, 
            descriptions=descriptions, 
            point_geometry=point_geometry, 
            complex_geometry=complex_geometry,
            object_finds=object_finds,
            maritime_craft=maritime_craft,
            historic_aircraft=historic_aircraft, 
            related_monument_records=related_monument_records,
            images=images,
            other_statuses=other_statuses,
            related_events=related_events,
            protected_statuses=protected_statuses,
            last_updated=last_updated
        )
        self.monumentSources = monument_sources
        self.monumentDatedTypes = monument_dated_types

    def __str__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName} ({self._resource_instance_id})"
