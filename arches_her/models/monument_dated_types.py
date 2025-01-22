from typing import List
from arches_her.hapi.helper import parse_date


class MonumentDatedTypes(object):
    def __init__(
        self,
        type: str,
        start_date: str,
        end_date: str,
        display_date: str,
        periods: List[str],
        materials: List[str],
        evidences: List[str]
    ):
        self.type = type
        self.startDate = parse_date(start_date)
        self.endDate = parse_date(end_date)
        self.displayDate = display_date
        self.periods = periods
        self.materials = materials
        self.evidences = evidences

    def __repr__(self):
        return f"MonumentDatedTypes(type={self.type}, startDate={self.startDate}, endDate={self.endDate}, displayDate={self.displayDate}, periods={self.periods}, materials={self.materials}, evidences={self.evidences})"
