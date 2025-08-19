import datetime
from typing import List
from arches_her.hapi.helper import parse_date
from .base_serializable import BaseSerializable


class MaritimeCraft(BaseSerializable):
    excluded_fields = set()

    def __init__(
        self,
        type: List[str],
        start_date: str,
        end_date: str,
        display_date: str,
        periods: List[str],
        materials: List[str]
    ):
        self.type = type
        self.start_date = parse_date(start_date)
        self.end_date = parse_date(end_date)
        self.display_date = display_date
        self.periods = periods
        self.materials = materials

    def __repr__(self):
        return f"MaritimeCraft(type={self.type}, start_date={self.start_date}, end_date={self.end_date}, display_date={self.display_date}, periods={self.periods}, materials={self.materials})"
