import datetime
import json
import os
from typing import List

from dateutil import parser
from popl.tpl.client import TPLClient

USER_ID = os.getenv('TPL_USER_ID')
CLIENT_ID = os.getenv('TPL_CLIENT_ID')
CLIENT_SECRET = os.getenv('TPL_CLIENT_SECRET')
PAGE_SIZE = 1000


def tpl_handler(request):
    now = datetime.datetime.utcnow()

    state = {
        'bookmarks': {
            'inventory': now.isoformat(),
        }
    }

    insert = {
        "inventory": get_inventory(),
    }

    return assemble_response_json(insert, state), 200, {"Content-Type": "application/json"}


def get_inventory():
    client = TPLClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_login_id=USER_ID)

    print('getting items from 3pl...')
    page = 1
    params = {'pgsiz': PAGE_SIZE, 'sort': 'receivedDate', 'pgnum': page}
    total_results = PAGE_SIZE
    results = []

    while total_results == PAGE_SIZE:
        print(f"fetching data for page: {page}")
        response = client.get("inventory", params=params)
        total_results = response.get('TotalResults', 0)
        print(f"total results: {total_results}")

        page += 1
        params.update({'pgnum': page})

        results.extend(response.get('ResourceList', []))

    return results


def get_bookmark(bookmarks: List, key: str) -> datetime.datetime:
    if not bookmarks:
        bookmarks = {}

    bookmark = bookmarks.get(key)
    if not bookmark:
        print(f"bookmark for {key} not found. Creating new bookmark")
        return datetime.datetime.utcnow()

    return parser.parse(bookmark)


def assemble_response_json(insert, state):
    response_dict = {
        "state": state,
        "schema": {
            "inventory": {
                "primary_key": [
                    "ReceiveItemId"
                ]
            }
        },
        "insert": insert,
        "hasMore": False
    }
    return json.dumps(response_dict)


if __name__ == '__main__':
    response = tpl_handler({})
    print(response)