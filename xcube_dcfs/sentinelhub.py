import json
import os
from typing import List, Any, Dict

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

    def process(self, request: Dict):
        resp = self.session.post(self.api_url + f'/process', json=request)
        obj = json.loads(resp.content)
        return obj
