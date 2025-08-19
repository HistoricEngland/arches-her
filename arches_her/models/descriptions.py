from .base_serializable import BaseSerializable

class Description(BaseSerializable):
    excluded_fields = set()

    def __init__(self, type: str, description: str):
        self.type = type
        self.description = description

    def __repr__(self):
        return f"Description(type={self.type}, description={self.description})"
