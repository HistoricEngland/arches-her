import unittest
from unittest.mock import patch, Mock
from arches_her.arches_her.functions.bngpoint_to_geojson_fn_orig import BNGPointToGeoJSON

class TestBNGPointToGeoJSON(unittest.TestCase):
    def setUp(self):
        self.bng_to_geojson = BNGPointToGeoJSON()
        self.bng_to_geojson.config = {'bng_node': 'bng_node', 'geojson_node': 'geojson_node', 'geojson_nodegroup': 'geojson_nodegroup'}

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_orig.Tile')
    def test_save_geojson(self, mock_tile):
        mock_request = Mock()        
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        mock_tile.nodegroup_id = 'geojson_nodegroup' # Mock the data attribute as a dictionary

        # # Mock the methods of the Tile class
        # mock_tile.objects.filter.return_value = []
        # mock_tile.get_blank_tile_from_nodegroup_id.return_value = Mock()

        # breakpoint()

        # Call the function with the mock objects
        self.bng_to_geojson.save_geojson(mock_tile, mock_request)

        
        # breakpoint()
        
        expected_result = {'type': 'Point', 'coordinates': [49.85153643668203, -7.565187626387456]}
        self.assertEqual(mock_tile.data['geojson_node']['features'][0]['geometry'], expected_result)


        # Assert that the methods were called with the correct arguments
        # mock_tile.objects.filter.assert_called_once_with(nodegroup_id=self.bng_to_geojson.config["geojson_nodegroup"], resourceinstance_id=mock_tile.resourceinstance_id)
        # mock_tile.get_blank_tile_from_nodegroup_id.assert_called_once_with(self.bng_to_geojson.config["geojson_nodegroup"], resourceid=mock_tile.resourceinstance_id, parenttile=tile.parenttile)

if __name__ == '__main__':
    unittest.main()