import datetime
import uuid
from typing import List, Tuple
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


class Resource():
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
        related_events: List[RelatedEvent],
        images: List[Image],
        protected_statuses: List[str],
        other_statuses: List[str],
        last_updated: datetime.datetime,
        delete: bool,
    ):
        self.resourceInstanceId = resource_instance_id
        self.primaryReferenceNumber = primary_reference_number
        self.heritageAssetName = heritage_asset_name
        self.descriptions = descriptions
        self.monumentDatedTypes = monument_dated_types
        self.pointGeometry = point_geometry
        self.complexGeometry = complex_geometry
        self.monumentSources = monument_sources
        self.objectFinds = object_finds
        self.maritimeCraft = maritime_craft
        self.historicAircraft = historic_aircraft
        self.relatedMonumentRecords = related_monument_records
        self.relatedEvents = related_events
        self.images = images
        self.protectedStatuses = protected_statuses
        self.otherStatuses = other_statuses
        self.lastUpdated = last_updated.strftime("%Y-%m-%dT%H:%M:%S")
        self.delete = delete

    def __repr__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName} ({self._resource_instance_id})"
