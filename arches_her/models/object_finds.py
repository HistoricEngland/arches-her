import datetime
from typing import List


class ObjectFinds(object):
    def __init__(
        self, 
        type: str, 
        start_date: datetime.datetime, 
        end_date: datetime.datetime, 
        display_date: str, 
        periods: List[str], 
        materials: List[str]
    ):
        self.type = type
        self.startDate = start_date
        self.endDate = end_date
        self.displayDate = display_date
        self.periods = periods
        self.materials = materials

    def __str__(self):
        return f"ObjectFinds(type={self.type}, startDate={self.startDate}, endDate={self.endDate}, displayDate={self.displayDate}, periods={self.periods}, materials={self.materials})"
