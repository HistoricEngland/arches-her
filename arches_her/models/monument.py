from typing import List
import datetime
import uuid


class Monument(object):
    def __init__(self, resource_instance_id: uuid.UUID, primary_reference_number: str, heritage_asset_name: str, descriptions: List[str], last_updated: datetime.datetime):
        self._resource_instance_id = resource_instance_id
        self.primaryReferenceNumber = primary_reference_number
        self.heritageAssetName = heritage_asset_name
        self.descriptions = descriptions
        self.lastUpdated = last_updated.astimezone(
            datetime.timezone.utc).isoformat()

    def __str__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName}"
