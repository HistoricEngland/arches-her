import datetime
import uuid
from typing import List, Tuple
from .historic_aircraft_data import HistoricAircraftData
from .maritime_craft import MaritimeCraft
from .object_finds import ObjectFinds
from .descriptions import Description
from .complex_geometry import ComplexGeometry
from .point_geometry import PointGeometry
from .related_monument_records import RelatedMonumentRecord
from .images import Image
from .related_events import RelatedEvent


class Base(object):
    def __init__(
        self,
        resource_instance_id: uuid.UUID,
        primary_reference_number: str,
        heritage_asset_name: str,
        descriptions: List[Description],
        point_geometry: PointGeometry,
        complex_geometry: List[ComplexGeometry],
        object_finds: List[ObjectFinds],
        maritime_craft: List[MaritimeCraft],
        historic_aircraft: List[HistoricAircraftData],
        related_monument_records: List[RelatedMonumentRecord],
        images: List[Image],
        other_statuses: List[str],
        related_events: List[RelatedEvent],
        protected_statuses: List[str],
        last_updated: datetime.datetime
    ):
        self.resourceInstanceId = resource_instance_id
        self.primaryReferenceNumber = primary_reference_number
        self.heritageAssetName = heritage_asset_name
        self.descriptions = descriptions
        self.pointGeometry = point_geometry
        self.complexGeometry = complex_geometry
        self.objectFinds = object_finds
        self.maritimeCraft = maritime_craft
        self.historicAircraft = historic_aircraft
        self.relatedMonumentRecords = related_monument_records
        self.images = images
        self.otherStatuses = other_statuses
        self.relatedEvents = related_events
        self.protectedStatuses = protected_statuses
        self.lastUpdated = last_updated.strftime("%Y-%m-%dT%H:%M:%S")
