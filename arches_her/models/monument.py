from typing import List, Tuple
import datetime
import uuid

from .base import Base
from .complex_geometry import ComplexGeometry
from .point_geometry import PointGeometry
from .descriptions import Description
from .monument_dated_types import MonumentDatedTypes
from .monument_sources import MonumentSource


class Monument(Base):
    def __init__(self, resource_instance_id: uuid.UUID, primary_reference_number: str, heritage_asset_name: str, descriptions: List[Description], monument_dated_types: List[MonumentDatedTypes], point_geometry: PointGeometry, complex_geometry: ComplexGeometry, monument_sources: List[MonumentSource], last_updated: datetime.datetime):
        super().__init__(resource_instance_id=resource_instance_id, primary_reference_number=primary_reference_number,
                         heritage_asset_name=heritage_asset_name, descriptions=descriptions, point_geometry=point_geometry, complex_geometry=complex_geometry, last_updated=last_updated)
        self.monumentSources = monument_sources
        self.monumentDatedTypes = monument_dated_types

    def __str__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName} ({self._resource_instance_id})"
