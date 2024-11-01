from typing import List
import datetime
import uuid
from .base import Base


class HistoricAircraft(Base):
    def __init__(self, resource_instance_id: uuid.UUID, primary_reference_number: str, heritage_asset_name: str, descriptions: List[str], last_updated: datetime.datetime):
        super().__init__(resource_instance_id, primary_reference_number,
                         heritage_asset_name, descriptions, last_updated)

    def __str__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName} ({self._resource_instance_id})"
