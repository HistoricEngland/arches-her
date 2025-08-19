from .base_serializable import BaseSerializable


class RelatedMonumentRecord(BaseSerializable):
    excluded_fields = set()

    def __init__(self, primary_reference_number: str, relationship: str):
        self.primaryReferenceNumber = primary_reference_number
        self.relationship = relationship

    def __repr__(self):
        return f"RelatedMonumentRecord(primaryReferenceNumber={self.primaryReferenceNumber}, relationship={self.relationship})"
