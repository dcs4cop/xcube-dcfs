import json
import os
import time
import unittest
from typing import Dict

from xcube_dcfs.sentinelhub import SentinelHub

HAS_SH_CREDENTIALS = 'SH_CLIENT_ID' in os.environ and 'SH_CLIENT_SECRET' in os.environ
REQUIRE_SH_CREDENTIALS = 'requires SH credentials'


class SentinelHubTest(unittest.TestCase):

    @unittest.skipUnless(HAS_SH_CREDENTIALS, REQUIRE_SH_CREDENTIALS)
    def test_get_data_single(self):
        with open_res('request-single.json') as fp:
            request = json.load(fp)

        sentinel_hub = SentinelHub()

        t1 = time.perf_counter()
        mime_type, data = sentinel_hub.get_data(request)
        t2 = time.perf_counter()
        print(f"test_get_data_single: took {t2 - t1} secs")

        self.assertEqual('application/tar', mime_type)
        # self.assertEqual('image/tif', mime_type)

        with open('response-single.tif', 'wb') as fp:
            fp.write(data)

        sentinel_hub.close()

    @unittest.skipUnless(HAS_SH_CREDENTIALS, REQUIRE_SH_CREDENTIALS)
    def test_get_data_multi(self):
        with open_res('request-multi.json') as fp:
            request = json.load(fp)

        sentinel_hub = SentinelHub()

        t1 = time.perf_counter()
        mime_type, data = sentinel_hub.get_data(request)
        t2 = time.perf_counter()
        print(f"test_get_data_multi: took {t2 - t1} secs")

        self.assertEqual('application/tar', mime_type)

        with open('response-multi.tar', 'wb') as fp:
            fp.write(data)

        sentinel_hub.close()

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
        sentinel_hub.close()

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
        sentinel_hub.close()

    def test_new_data_request_single(self):
        request = SentinelHub.new_data_request(
            'S2L1C',
            ['B02'],
            (512, 512),
            time_range=("2018-10-01T00:00:00.000Z", "2018-10-10T00:00:00.000Z"),
            bbox=(
                13.822,
                45.850,
                14.559,
                46.291,
            ),
            sample_types="INT8",
        )

        # with open('request-single.json', 'w') as fp:
        #     json.dump(request, fp, indent=2)

        with open_res('request-single.json') as fp:
            expected_request = json.load(fp)

        self.assertEqual(expected_request, request)

    def test_new_data_request_multi(self):
        request = SentinelHub.new_data_request(
            'S2L1C',
            ['B02', 'B03', 'B04', 'B08'],
            (512, 512),
            time_range=("2018-10-01T00:00:00.000Z", "2018-10-10T00:00:00.000Z"),
            bbox=(
                13.822,
                45.850,
                14.559,
                46.291,
            ),
            sample_types="INT8",
        )

        # with open('request-multi.json', 'w') as fp:
        #     json.dump(request, fp, indent=2)

        with open_res('request-multi.json') as fp:
            expected_request = json.load(fp)

        self.assertEqual(expected_request, request)


class SessionMock:
    def __init__(self, mapping: Dict):
        self.mapping = mapping

    # noinspection PyUnusedLocal
    def get(self, url, **kwargs):
        return self._response(self.mapping['get'][url])

    # noinspection PyUnusedLocal
    def post(self, url, **kwargs):
        return self._response(self.mapping['post'][url])

    def close(self):
        pass

    @classmethod
    def _response(cls, obj):
        return SessionResponseMock(content=json.dumps(obj))


class SessionResponseMock:
    def __init__(self, content=None):
        self.content = content


def open_res(file_path: str):
    return open(os.path.join(os.path.dirname(__file__), file_path), 'r')
