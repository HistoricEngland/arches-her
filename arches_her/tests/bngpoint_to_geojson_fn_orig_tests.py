import unittest
from unittest.mock import patch, Mock
from arches_her.arches_her.functions.bngpoint_to_geojson_fn_orig import BNGPointToGeoJSON


# root@2ff68380857c:/web_root/arches#  python manage.py test ../arches_her/arches_her/tests/bngpoint_to_geojson_fn_orig_tests.py  --pattern="*.py" --settings="tests.test_settings"
class TestBNGPointToGeoJSON(unittest.TestCase):
    def setUp(self):
        self.bng_to_geojson = BNGPointToGeoJSON()
        self.bng_to_geojson.config = {'bng_node': 'bng_node', 'geojson_node': 'geojson_node', 'geojson_nodegroup': 'geojson_nodegroup'}

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_orig.Tile')
    def test_save_geojson(self, mock_tile):
        mock_request = Mock()        
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        # Mock the data attribute of the Tile object.
        mock_tile.nodegroup_id = 'geojson_nodegroup' 

        # Call the function with the mock objects
        self.bng_to_geojson.save_geojson(mock_tile, mock_request)

        # Assert that the geojson_node attribute of the tile object is as expected.        
        expected_result = {'type': 'Point', 'coordinates': [49.85153643668203, -7.565187626387456]}
        self.assertEqual(mock_tile.data['geojson_node']['features'][0]['geometry'], expected_result)


    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_orig.Tile')
    def test_save_geojson_previously_saved_tiles(self, mock_tile):
        mock_request = Mock()        
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        # We don't expect this to be found in the config. It's just a dummy value to test the else block.
        mock_tile.nodegroup_id = 'animal food trough wiper' 

        # Mock the methods of the Tile class
        mock_tile.objects.filter.return_value = []
        mock_tile.get_blank_tile_from_nodegroup_id.return_value = Mock()

        # Call the function with the mock objects
        self.bng_to_geojson.save_geojson(mock_tile, mock_request)

        # Assert that the methods were called with the correct arguments
        mock_tile.objects.filter.assert_called_once_with(nodegroup_id=self.bng_to_geojson.config["geojson_nodegroup"],
                                                         resourceinstance_id=mock_tile.resourceinstance_id)
        
        # N.b get_blank_tile_from_nodegroup_id is not a direct method of mock_tile. Instead, it's a method of the object returned by mock_tile(),
        # therefore get_blank_tile_from_nodegroup_id method is called on the result of mock_tile(), not directly on mock_tile.
        mock_tile().get_blank_tile_from_nodegroup_id.assert_called_once_with(self.bng_to_geojson.config["geojson_nodegroup"],
                                                                             resourceid=mock_tile.resourceinstance_id,
                                                                             parenttile=mock_tile.parenttile)

if __name__ == '__main__':
    unittest.main()