from typing import List, Tuple
import datetime
import uuid


class Base(object):
    def __init__(self, resource_instance_id: uuid.UUID, primary_reference_number: str, heritage_asset_name: str, descriptions: List[str], point_geometry: Tuple[float, float], complex_geometry: Tuple[str, str], last_updated: datetime.datetime):
        self._resource_instance_id = resource_instance_id
        self.primaryReferenceNumber = primary_reference_number
        self.heritageAssetName = heritage_asset_name
        self.descriptions = descriptions
        self.pointGeometry = point_geometry
        self.complexGeometry = complex_geometry
        self.lastUpdated = last_updated.astimezone(
            datetime.timezone.utc).isoformat()
