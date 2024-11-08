from typing import List


class RelatedEvent:
    def __init__(self, primary_reference_number: str, types: List[str], name: str, description: str, url: str):
        self.primaryReferenceNumber = primary_reference_number
        self.types = types
        self.name = name
        self.description = description
        self.url = url

    def __str__(self):
        return f"{self.primaryReferenceNumber} {self.name} ({self.types})"
