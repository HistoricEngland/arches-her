class PointGeometry(object):
    def __init__(self, reference_system: str = "EPSG 4326", x_coordinate: float = 0.0, y_coordinate: float = 0.0):
        self.referenceSystem = reference_system
        self.xCoordinate = x_coordinate
        self.yCoordinate = y_coordinate

    def __str__(self):
        return f"PointGeometry(referenceSystem={self.referenceSystem}, xCoordinate={self.xCoordinate}, yCoordinate={self.yCoordinate})"
