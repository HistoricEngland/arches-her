import datetime
from typing import List
from arches_her.hapi.helper import parse_date
from .base_serializable import BaseSerializable


class HistoricAircraftData(BaseSerializable):
    excluded_fields = set()

    def __init__(
        self,
        type: str,
        start_date: datetime.date,
        end_date: datetime.date,
        display_date: str,
        periods: List[str],
        materials: List[str]
    ):
        self.type = type
        self.startDate = parse_date(start_date)
        self.endDate = parse_date(end_date)
        self.displayDate = display_date
        self.periods = periods
        self.materials = materials

    def __repr__(self):
        return f"HistoricAircraftData(type={self.type}, start_date={self.startDate}, end_date={self.endDate}, display_date={self.displayDate}, periods={self.periods}, materials={self.materials})"
