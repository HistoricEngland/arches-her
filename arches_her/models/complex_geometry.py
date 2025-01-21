class ComplexGeometry(object):
    def __init__(
        self,
        spatial_feature_type: str,
        spatial_feature_geometry: str,
        reference_system: str = "EPSG 4326",
        spatial_feature_geometry_format: str = "wkt"
    ):
        self.spatialFeatureType = self.get_spatial_feature_type(spatial_feature_type)
        self.referenceSystem = reference_system
        self.spatialFeatureGeometryFormat = spatial_feature_geometry_format
        self.spatialFeatureGeometry = spatial_feature_geometry

    def __repr__(self):
        return (
            f"ComplexGeometry(spatialFeatureType={self.spatialFeatureType}, "
            f"referenceSystem={self.referenceSystem}, "
            f"spatialFeatureGeometryFormat={self.spatialFeatureGeometryFormat}, "
            f"spatialFeatureGeometry={self.spatialFeatureGeometry})"
        )

    def get_spatial_feature_type(self, spatial_feature_type: str) -> str:
        type_mapping = {
            "MULTIPOINT": "multipoint",
            "MULTILINESTRING": "multilinestring",
            "MULTIPOLYGON": "multipolygon",
            "GEOMETRYCOLLECTION": "collection"
        }

        # Return the mapped value if it exists, otherwise return the input value in lowercase
        return type_mapping.get(spatial_feature_type, spatial_feature_type.lower())
