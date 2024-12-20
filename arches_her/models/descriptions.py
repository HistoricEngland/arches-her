class Description(object):
    def __init__(self, type: str, description: str):
        self.type = type
        self.description = description

    def __str__(self):
        return f"Description(type={self.type}, description={self.description})"
