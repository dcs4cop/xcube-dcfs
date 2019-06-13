import json
import os
from typing import List, Any, Dict, Tuple, Union, Sequence

import oauthlib.oauth2
import requests_oauthlib

DEFAULT_OAUTH2_URL = 'https://services.sentinel-hub.com/oauth'
DEFAULT_API_URL = 'https://services.sentinel-hub.com/api/v1'


class SentinelHub:
    def __init__(self,
                 client_id=None,
                 client_secret=None,
                 session=None,
                 api_url=DEFAULT_API_URL,
                 oauth2_url=DEFAULT_OAUTH2_URL):
        self.api_url = api_url
        self.oauth2_url = oauth2_url
        if session is None:
            # Client credentials
            client_id = client_id or os.environ.get('SH_CLIENT_ID')
            client_secret = client_secret or os.environ.get('SH_CLIENT_SECRET')

            # Create a OAuth2 session
            client = oauthlib.oauth2.BackendApplicationClient(client_id=client_id)
            self.session = requests_oauthlib.OAuth2Session(client=client)

            # Get OAuth2 token for the session
            self.token = self.session.fetch_token(token_url=oauth2_url + '/token',
                                                  client_id=client_id,
                                                  client_secret=client_secret)
        else:
            self.session = session
            self.token = None

    def close(self):
        self.session.close()

    @property
    def token_info(self) -> Dict[str, Any]:
        resp = self.session.get(self.oauth2_url + '/tokeninfo')
        return json.loads(resp.content)

    # noinspection PyMethodMayBeStatic
    @property
    def dataset_names(self) -> List[str]:
        resp = self.session.get(self.api_url + '/process/dataset')
        obj = json.loads(resp.content)
        return obj.get('data')

    def band_names(self, dataset_name) -> Dict[str, Any]:
        resp = self.session.get(self.api_url + f'/process/dataset/{dataset_name}/bands')
        obj = json.loads(resp.content)
        return obj.get('data')

    def get_data(self, request: Dict) -> Tuple[str, Any]:
        outputs = request['output']['responses']
        accept_header = 'application/tar'  # if len(outputs) > 1 else 'image/tiff'
        resp = self.session.post(self.api_url + f'/process', json=request,
                                 headers={
                                     'Accept': accept_header,
                                     'cache-control': 'no-cache'
                                 })

        if not resp.ok:
            raise SentinelHubError(resp.reason,
                                   status_code=resp.status_code,
                                   content=resp.content)

        return accept_header, resp.content

    @classmethod
    def new_data_request(cls,
                         dataset_name: str,
                         band_names: Sequence[str],
                         size: Tuple[int, int],
                         time_range: Tuple[str, str] = None,
                         bbox: Tuple[float, float, float, float] = None,
                         upsampling: str = 'BILINEAR',
                         downsampling: str = 'BILINEAR',
                         band_units: Union[str, Sequence[str]] = 'reflectance',
                         sample_types: Union[str, Sequence[str]] = 'FLOAT32') -> Dict:

        if bbox is None:
            bbox = [-180., -90., 180., 90.]

        if isinstance(band_units, str):
            band_units = [band_units] * len(band_names)

        if isinstance(sample_types, str):
            sample_types = [sample_types] * len(band_names)

        data_element = {
            "type": dataset_name,
            "processing": {
                "upsampling": upsampling,
                "downsampling": downsampling
            },
        }

        if time_range is not None:
            time_range_from, time_range_to = time_range
            time_range_element = {}
            if time_range_from:
                time_range_element['from'] = str(time_range_from)
            if time_range_to:
                time_range_element['to'] = str(time_range_to)
            data_element["dataFilter"] = dict(timeRange=time_range_element)

        input_element = {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/OGC/9.5.3/CRS84"
                }
            },
            "data": [data_element]
        }

        width, height = size
        responses_element = []

        for band_name in band_names:
            responses_element.append({
                "identifier": band_name,
                "format": {
                    "type": "image/tiff"
                }
            })

        output_element = {
            "width": width,
            "height": height,
            "responses": responses_element
        }

        evalscript = []
        evalscript.extend([
            "//VERSION=3",
            "function setup() {",
            "    return {",
            "        input: [{",
            "            bands: [" + ", ".join(map(repr, band_names)) + "],",
            "            units: [" + ", ".join(map(repr, band_units)) + "],",
            "        }],",
            "        output: [",
        ])
        evalscript.extend(["            {id: " + repr(band_name) + ", bands: 1, sampleType: " + repr(sample_type) + "},"
                           for band_name, sample_type in zip(band_names, sample_types)])
        evalscript.extend([
            "        ]",
            "    };",
            "}"
        ])
        # if len(band_names) > 1:
        if len(band_names) > 0:
            evalscript.extend([
                "function evaluatePixel(sample) {",
                "    return {",
            ])
            evalscript.extend(["        " + band_name + ": [sample." + band_name + "]," for band_name in band_names])
            evalscript.extend([
                "    };",
                "}",
            ])
        else:
            # Doesn't work, buts docs say so: https://docs.sentinel-hub.com/api/latest/#/Evalscript/V3/README
            evalscript.extend([
                "function evaluatePixel(sample) {",
                "    return [sample." + band_names[0] + "];",
                "}",
            ])

        # Convert into valid JSON
        return json.loads(json.dumps({
            "input": input_element,
            "output": output_element,
            "evalscript": "\n".join(evalscript)
        }))


class SentinelHubError(Exception):
    def __init__(self, reason, status_code, content=None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.content = content

    def __repr__(self) -> str:
        return f'SentinelHubError({self.reason}, {self.status_code}, details={self.content!r})'

    def __str__(self) -> str:
        text = f'{self.reason}, status code {self.status_code}'
        if self.content:
            text += f':\n{self.content}\n'
        return text
