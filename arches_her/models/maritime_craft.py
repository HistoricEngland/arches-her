from typing import List
import datetime


class MaritimeCraft(object):
    def __init__(
        self, 
        type: List[str], 
        start_date: datetime.date, 
        end_date: datetime.date, 
        display_date: str, 
        periods: List[str], 
        materials: List[str]
    ):
        self.type = type
        self.start_date = start_date
        self.end_date = end_date
        self.display_date = display_date
        self.periods = periods
        self.materials = materials

    def __str__(self):
        return f"MaritimeCraft(type={self.type}, start_date={self.start_date}, end_date={self.end_date}, display_date={self.display_date}, periods={self.periods}, materials={self.materials})"
