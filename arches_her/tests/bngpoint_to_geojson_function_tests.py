import unittest
from unittest.mock import Mock, patch
from functions.bngpoint_to_geojson_function import BNGPointToGeoJSON

class TestBNGPointToGeoJSON(unittest.TestCase):
    def setUp(self):
        self.bng_to_geojson = BNGPointToGeoJSON()

    @patch('bngpoint_to_geojson_function.Tile')
    def test_save_geojson(self, mock_tile):
        mock_request = Mock()
        mock_tile.data = {'bng_node': 'NA123456'}
        self.bng_to_geojson.config = {'bng_node': 'bng_node', 'geojson_node': 'geojson_node', 'geojson_nodegroup': 'geojson_nodegroup'}
        self.bng_to_geojson.save_geojson(mock_tile, mock_request, True)
        self.assertIsNotNone(mock_tile.data['geojson_node'])

    @patch('bngpoint_to_geojson_function.Tile')
    def test_save(self, mock_tile):
        mock_request = Mock()
        self.bng_to_geojson.save(mock_tile, mock_request)
        mock_tile.assert_called_once()

    @patch('bngpoint_to_geojson_function.Tile')
    def test_on_import(self, mock_tile):
        self.bng_to_geojson.on_import(mock_tile)
        mock_tile.assert_called_once()

if __name__ == '__main__':
    unittest.main()