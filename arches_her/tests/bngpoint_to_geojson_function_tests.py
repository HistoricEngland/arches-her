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

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test__transform_bng_to_geojson_validBNG(self, mock_tile):
        bngValueReturned = 'NA123456'  
        expectedResult = {'type': 'Point', 'coordinates': [49.85153643668203, -7.565187626387456]}
        transformationResult = self.bng_to_geojson._transform_bng_to_geojson(bngValueReturned)
        self.assertEqual(expectedResult, transformationResult)    

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test__transform_bng_to_geojson_non_validBNG(self, mock_tile):
        bngValueReturned = 'empty-headed animal-food-trough wiper'
        with self.assertRaises(ValueError) as context:
            self.bng_to_geojson._transform_bng_to_geojson(bngValueReturned)
            
        self.assertTrue("Unable to Transform BNG value. Please check the value is correct." in str(context.exception))
        
    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_function.Tile')
    def test_is_function_call(self, mock_tile):
        mock_request = Mock()
        # Test when request is None and is_function_save_method is True
        result = self.bng_to_geojson._is_function_call(None, True)
        self.assertTrue(result)

        # Test when request is not None and is_function_save_method is True
        result = self.bng_to_geojson._is_function_call(mock_request, True)
        self.assertFalse(result)

        # Test when request is None and is_function_save_method is False
        result = self.bng_to_geojson._is_function_call(None, False)
        self.assertFalse(result)

        # Test when request is not None and is_function_save_method is False
        result = self.bng_to_geojson._is_function_call(mock_request, False)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()