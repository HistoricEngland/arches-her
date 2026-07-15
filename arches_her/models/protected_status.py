from typing import List, Optional
from .base_serializable import BaseSerializable


class ProtectedStatus(BaseSerializable):
    excluded_fields = set()

    def __init__(self, protected_statuses: Optional[List[str]] = None):
        if protected_statuses is None:
            self.protectedStatuses = []
        else:
            self.protectedStatuses = protected_statuses

    def __repr__(self):
        return f"ProtectedStatus(protectedStatuses={self.protectedStatuses})"
