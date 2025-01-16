from typing import List


class RelatedEvent:
    def __init__(self, primary_reference_number: str, types: List[str], name: str, description: str):
        self.primaryReferenceNumber = primary_reference_number
        self.types = types
        self.name = name
        self.description = description

    def __repr__(self):
        return f"RelatedEvent(primaryReferenceNumber={self.primaryReferenceNumber}, types={self.types}, name={self.name}, description={self.description})"
