import datetime
import json
import os
from typing import List

from dateutil import parser
from popl.rakuten.client import RakutenClient

CLIENT_ID = os.getenv('RAKUTEN_CLIENT_ID')
USER_ID = os.getenv('RAKUTEN_API_USER_ID')
USER_SECRET = os.getenv('RAKUTEN_API_SECRET')
PAGE_SIZE = 1000


def rakuten_handler(request):
    now = datetime.datetime.utcnow()

    state = {
        'bookmarks': {
            'items': now.isoformat(),
        }
    }

    insert = {
        "items": get_items_data(),
    }

    return assemble_response_json(insert, state), 200, {"Content-Type": "application/json"}


def get_items_data():
    client = RakutenClient(CLIENT_ID, USER_ID, USER_SECRET)

    print('getting items from rakuten...')
    page = 1
    page_size = PAGE_SIZE
    params = {'pageSize': page_size, 'page': page}
    paginate = True
    running_total = 0
    results = []

    while paginate:
        response = client.get_items(params=params)
        total_results = response['pageMetadata']['totalResults']
        running_total += page_size
        print(f"total results: {total_results}")
        print(f"running total: {running_total}")

        paginate = running_total < total_results
        page += 1
        params.update({'page': page})
        print(f"fetching data for page: {page}")

        results.extend(response['data'])


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
            "items": {
                "primary_key": [
                    "stockKeepingUnit"
                ]
            }
        },
        "insert": insert,
        "hasMore": False
    }
    return json.dumps(response_dict)


if __name__ == '__main__':
    response = rakuten_handler({})
    print(response)