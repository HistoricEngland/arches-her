from typing import List
import datetime


class HistoricAircraftData(object):
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
        self.startDate = start_date
        self.endDate = end_date
        self.displayDate = display_date
        self.periods = periods
        self.materials = materials

    def __str__(self):
        return f"HistoricAircraftData(type={self.type}, start_date={self.startDate}, end_date={self.endDate}, display_date={self.displayDate}, periods={self.periods}, materials={self.materials})"
