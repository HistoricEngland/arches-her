class BaseSerializable:
    # Class-level set of excluded fields (can be overridden per class or instance)
    excluded_fields = set()

    def to_dict(self, exclude_fields=None):
        exclude_fields = set(
            exclude_fields) if exclude_fields else self.excluded_fields
        fields = {k: v for k, v in self.__dict__.items()
                  if k not in exclude_fields}
        # Flatten if only one property remains and its value is a list
        if len(fields) == 1:
            value = next(iter(fields.values()))
            if isinstance(value, list):
                return value
        return fields if fields else None
