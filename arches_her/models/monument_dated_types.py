from typing import List


class MonumentDatedTypes(object):
    def __init__(
        self, 
        type: List[str], 
        start_date: str, 
        end_date: str, 
        display_date: str, 
        periods: List[str], 
        materials: List[str], 
        evidences: List[str]
    ):
        self.type = type
        self.startDate = start_date
        self.endDate = end_date
        self.displayDate = display_date
        self.periods = periods
        self.materials = materials
        self.evidences = evidences

    def __str__(self):
        return f"MonumentDatedTypes(type={self.type}, startDate={self.startDate}, endDate={self.endDate}, displayDate={self.displayDate}, periods={self.periods}, materials={self.materials}, evidences={self.evidences})"
