import json
import os
import unittest
from typing import Dict

from xcube_dcfs.sentinelhub import SentinelHub


class SentinelHubTest(unittest.TestCase):

    @unittest.skipUnless('SH_CLIENT_ID' in os.environ and 'SH_CLIENT_SECRET' in os.environ,
                         "requires SH credentials")
    def test_process(self):
        with open_res('evalscript.js') as fp:
            evalscript = fp.read()

        with open_res('request.json') as fp:
            request = json.load(fp)
            request['evalscript'] = evalscript

        print(json.dumps(request, indent=2))

        sentinel_hub = SentinelHub()
        response = sentinel_hub.process(request)
        print(response)

    def test_dataset_names(self):
        expected_dataset_names = ["DEM", "S2L1C", "S2L2A", "CUSTOM", "S1GRD"]
        sentinel_hub = SentinelHub(session=SessionMock({
            'get': {
                'https://services.sentinel-hub.com/api/v1/process/dataset': {
                    "data": expected_dataset_names
                }
            }}))
        self.assertEqual(expected_dataset_names, sentinel_hub.dataset_names)

    def test_band_names(self):
        expected_band_names = ['B01',
                               'B02',
                               'B03',
                               'B04',
                               'B05',
                               'B06',
                               'B07',
                               'B08',
                               'B8A',
                               'B09',
                               'B10',
                               'B11',
                               'B12',
                               'viewZenithMean',
                               'viewAzimuthMean',
                               'sunZenithAngles',
                               'sunAzimuthAngles']
        sentinel_hub = SentinelHub(session=SessionMock({
            'get': {
                'https://services.sentinel-hub.com/api/v1/process/dataset/S2L2A/bands': {
                    'data': expected_band_names
                }
            }
        }))
        self.assertEqual(expected_band_names, sentinel_hub.band_names('S2L2A'))

    def test_token_info(self):
        expected_token_info = {
            'sub': '1f3eee48-2f31-4453-97ad-50779a0c6caa',
            'aud': 'a28363fd-6733-4924-b77c-912862ef246b',
            'jti': 'a49f59e39165ba922a49c434f8961669',
            'exp': 1560353807,
            'name': 'Norman Fomferra',
            'email': 'norman.fomferra@brockmann-consult.de',
            'given_name': 'Norman',
            'family_name': 'Fomferra',
            'sid': '61aa8c3f-5fa3-46ab-a2c1-97deacba0d45',
            'active': True
        }
        sentinel_hub = SentinelHub(session=SessionMock({
            'get': {
                'https://services.sentinel-hub.com/oauth/tokeninfo':
                    expected_token_info
            }
        }))
        self.assertEqual(expected_token_info, sentinel_hub.token_info)


class SessionMock:
    def __init__(self, mapping: Dict):
        self.mapping = mapping

    def get(self, url):
        return self._response(self.mapping['get'][url])

    def post(self, url):
        return self._response(self.mapping['post'][url])

    @classmethod
    def _response(cls, obj):
        return SessionResponseMock(content=json.dumps(obj))


class SessionResponseMock:
    def __init__(self, content=None):
        self.content = content


def open_res(file_path: str):
    return open(os.path.join(os.path.dirname(__file__), file_path), 'r')
