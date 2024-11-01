from typing import List
import datetime
import uuid
from .monument import Monument
from .historic_aircraft import HistoricAircraft
from .maritime_vessel import MaritimeVessel


def create_resource(resource_type: str, resource_instance_id: uuid.UUID, primary_reference_number: str, heritage_asset_name: str, descriptions: List[str], last_updated: datetime.datetime):
    if resource_type == "Monument":
        return Monument(resource_instance_id, primary_reference_number, heritage_asset_name, descriptions, last_updated)
    elif resource_type == "Historic Aircraft":
        return HistoricAircraft(resource_instance_id, primary_reference_number, heritage_asset_name, descriptions, last_updated)
    elif resource_type == "Maritime Vessel":
        return MaritimeVessel(resource_instance_id, primary_reference_number, heritage_asset_name, descriptions, last_updated)
    else:
        raise ValueError(f"Unknown resource type: {resource_type}")
