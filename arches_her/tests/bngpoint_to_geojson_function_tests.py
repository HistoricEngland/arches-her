#from django.contrib.auth.models import User
# rest of your code
import unittest
from unittest.mock import Mock, patch
from arches_her.arches_her.functions.bngpoint_to_geojson_function import BNGPointToGeoJSON

class TestBNGPointToGeoJSON(unittest.TestCase):
    def setUp(self):
        self.bng_to_geojson = BNGPointToGeoJSON()
        self.bng_to_geojson.config = {'bng_node': 'bng_node', 'geojson_node': 'geojson_node', 'geojson_nodegroup': 'geojson_nodegroup'}

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test_save_geojson(self, mock_tile):
        mock_request = Mock()
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        mock_tile.nodegroup_id = 'geojson_nodegroup'
        self.bng_to_geojson.save_geojson(mock_tile, mock_request, True)
        import pdb; pdb.set_trace()
        self.assertIsNotNone(mock_tile.data['geojson_node'])

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test_save(self, mock_tile):
        mock_request = Mock()
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        self.bng_to_geojson.save(mock_tile, mock_request)
        mock_tile.assert_called_once()

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test_on_import(self, mock_tile):
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        self.bng_to_geojson.on_import(mock_tile)
        mock_tile.assert_called_once()

if __name__ == '__main__':
    unittest.main()