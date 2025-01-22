import datetime
from typing import List
from arches_her.hapi.helper import parse_date


class ObjectFinds(object):
    def __init__(
        self,
        type: List[str],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        periods: List[str],
        materials: List[str]
    ):
        self.type = type
        self.startDate = parse_date(start_date)
        self.endDate = parse_date(end_date)
        self.periods = periods
        self.materials = materials

    def __repr__(self):
        return f"ObjectFinds(type={self.type}, startDate={self.startDate}, endDate={self.endDate}, periods={self.periods}, materials={self.materials})"
