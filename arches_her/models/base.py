from typing import List, Tuple
import datetime
import uuid

from .object_finds import ObjectFinds
from .descriptions import Description
from .complex_geometry import ComplexGeometry
from .point_geometry import PointGeometry


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
        last_updated: datetime.datetime
    ):
        self._resource_instance_id = resource_instance_id
        self.primaryReferenceNumber = primary_reference_number
        self.heritageAssetName = heritage_asset_name
        self.descriptions = descriptions
        self.pointGeometry = point_geometry
        self.complexGeometry = complex_geometry
        self.objectFinds = object_finds
        self.lastUpdated = last_updated.strftime("%Y-%m-%dT%H:%M:%S")
