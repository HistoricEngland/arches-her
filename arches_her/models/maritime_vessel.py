import datetime
import uuid
from typing import List
from .base import Base
from .complex_geometry import ComplexGeometry
from .descriptions import Description
from .point_geometry import PointGeometry


class MaritimeVessel(Base):
    def __init__(
        self,
        resource_instance_id: uuid.UUID,
        primary_reference_number: str,
        heritage_asset_name: str,
        descriptions: List[Description],
        point_geometry: PointGeometry,
        complex_geometry: ComplexGeometry,
        last_updated: datetime.datetime
    ):
        super().__init__(
            resource_instance_id=resource_instance_id,
            primary_reference_number=primary_reference_number,
            heritage_asset_name=heritage_asset_name,
            descriptions=descriptions,
            point_geometry=point_geometry,
            complex_geometry=complex_geometry,
            last_updated=last_updated
        )

    def __repr__(self):
        return f"{self.primaryReferenceNumber} {self.heritageAssetName} ({self._resource_instance_id})"
