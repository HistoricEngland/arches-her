#from django.contrib.auth.models import User
# rest of your code
import unittest
from unittest.mock import Mock, patch
from arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd import BNGPointToGeoJSON

# root@b380c6f689a5:/web_root/arches#  python manage.py test ../arches_her/arches_her/tests/bngpoint_to_geojson_fn_refctd_tests.py  --pattern="*.py" --settings="tests.test_settings"
class TestBNGPointToGeoJSON(unittest.TestCase):

    def setUp(self):
        self.bng_to_geojson = BNGPointToGeoJSON()
        self.bng_to_geojson.config = {'bng_node': 'bng_node', 'geojson_node': 'geojson_node', 'geojson_nodegroup': 'geojson_nodegroup'}

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test__save_geojson(self, mock_tile):
        mock_request = Mock()
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        mock_tile.nodegroup_id = 'geojson_nodegroup'
        self.bng_to_geojson._save_geojson(mock_tile, mock_request, True)
        self.assertIsNotNone(mock_tile.data['geojson_node'])

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test_save(self, mock_tile):
        mock_request = Mock()
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        self.bng_to_geojson.save(mock_tile, mock_request)
        mock_tile.assert_called_once()

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test_on_import(self, mock_tile):
        mock_tile.data = {'bng_node': 'NA123456', 'geojson_node': None}
        self.bng_to_geojson.on_import(mock_tile)
        mock_tile.assert_called_once()

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test__transform_bng_to_geojson_validBNG(self, mock_tile):
        bngValueReturned = 'NA123456'  
        expectedResult = {'type': 'Point', 'coordinates': [49.85153643668203, -7.565187626387456]}
        transformationResult = self.bng_to_geojson._transform_bng_to_geojson(bngValueReturned)
        self.assertEqual(expectedResult, transformationResult)    

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test__transform_bng_to_geojson_non_validBNG(self, mock_tile):
        bngValueReturned = 'empty-headed animal-food-trough wiper'
        with self.assertRaises(ValueError) as context:
            self.bng_to_geojson._transform_bng_to_geojson(bngValueReturned)
            
        self.assertTrue("Unable to Transform BNG value. Please check the value is correct." in str(context.exception))
        
    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test__is_function_call(self, mock_tile):
        mock_request = Mock()
        result = self.bng_to_geojson._is_function_call(None, True)
        self.assertTrue(result)

        result = self.bng_to_geojson._is_function_call(mock_request, True)
        self.assertFalse(result)

        result = self.bng_to_geojson._is_function_call(None, False)
        self.assertFalse(result)

        result = self.bng_to_geojson._is_function_call(mock_request, False)
        self.assertFalse(result)

    @patch('arches_her.arches_her.functions.bngpoint_to_geojson_fn_refctd.Tile')
    def test__create_geojson_object(self, mock_tile):
        bngValueReturned = 'NA123456'
        pointGeoJSON = {'type': 'Point', 'coordinates': [49.85153643668203, -7.565187626387456]}

        result = self.bng_to_geojson._create_geojson_object(bngValueReturned, pointGeoJSON)

        # 'id' and 'datetime' will vary each run, and do not require testing.
        for feature in result['features']:
            feature['properties'].pop('datetime', None)
            feature.pop('id', None)

        expectedResult = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'geometry': pointGeoJSON,
                    'type': 'Feature',
                    'properties': {'bngref': bngValueReturned}
                }
            ]
        }            

        self.assertDictEqual(result, expectedResult)

if __name__ == '__main__':
    unittest.main()