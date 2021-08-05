import json

from popl.rakuten.errors import raise_for_error
from requests import Session


class RakutenClient:
    base_url = 'https://api.rakutensl.com'

    def __init__(self, client_id: int, api_user: str, api_secret:str):
        self._client_id = client_id
        self._api_user = api_user
        self._api_secret = api_secret
        self._session = Session()
        self._access_token = None

    def _build_auth_body(self):
        return json.dumps({
            "clientId": self._client_id,
            "apiUserIdentifier": self._api_user,
            "apiUserSecret": self._api_secret,
        })

    def _get_access_token(self):
        url = self._build_url('/Auth')
        data = self._build_auth_body()
        headers = {'Content-Type': 'application/json'}

        response = self._post(url, headers=headers, data=data)

        self._access_token = response['data']['token']

    def _build_url(self, endpoint):
        return f"{self.base_url}{endpoint}"

    def _get(self, url, headers=None, params=None, data=None):
        return self._make_request(url, method='GET', headers=headers, params=params, data=data)

    def _post(self, url, headers=None, params=None, data=None):
        return self._make_request(url, method='POST', headers=headers, params=params, data=data)

    def _make_request(self, url, method, headers=None, params=None, data=None):

        if not headers:
            headers = self._get_headers()

        with self._session as session:
            response = session.request(method, url, headers=headers, params=params, data=data)

            if response.status_code != 200:
                raise_for_error(response)
                return None

            return response.json()

    def _get_headers(self):
        return {
            'ClientId': str(self._client_id),
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json',
        }

    def get_items(self, *args, **kwargs):
        self._get_access_token()
        url = self._build_url('/Items')
        return self._get(url)
