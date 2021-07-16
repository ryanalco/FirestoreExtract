import datetime
import json
from typing import List, Tuple

from dateutil import parser
from sp_api.api import Inventories, Sales
from sp_api.base.sales_enum import Granularity


def handler(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    request_json = request.get_json()
    bookmarks = request_json.get('state', {}).get('bookmarks')
    sales_bookmark = get_bookmark(bookmarks, 'sales')
    inventories_bookmark = get_bookmark(bookmarks, 'inventories')

    state = {
        'bookmarks': {
            'sales': sales_bookmark.isoformat(),
            'inventories': inventories_bookmark.isoformat(),
        }
    }

    insert = {
        "sales": get_sales(sales_bookmark),
        "inventories": get_inventories()
    }

    return assemble_response_json(insert, state), 200, {"Content-Type": "application/json"}


def get_inventories():
    """Get inventories data.
    Docs: https://github.com/amzn/selling-partner-api-docs/blob/main/references/fba-inventory-api/fbaInventory.md#getinventorysummariesresponse
    """
    # client = Inventories().get_inventory_summary_marketplace()
    return []


def get_sales(datetimeobj):
    """Get aggregated sales info.
    Docs: https://github.com/amzn/selling-partner-api-docs/blob/8438231aefe8dfbdf7c1758ddf137a0c728bb21b/references/sales-api/sales.md#getordermetricsresponse
    """

    print("getting sales data...")
    interval = create_date_interval(datetimeobj)
    client = Sales()
    response = client.get_order_metrics(interval=interval, granularity=Granularity.HOUR)

    return response.payload


def assemble_response_json(insert, state):
    response_dict = {
        "state": state,
        "schema": {
            "inventories": {
                "primary_key": [
                    "id"
                ]
            },
            "sales": {
                "primary_key": [
                    "interval"
                ]
            }
        },
        "insert": insert,
        "hasMore": False
    }
    return json.dumps(response_dict)


def create_date_interval(datetimeobj: datetime.datetime, hours=1) -> Tuple[datetime.datetime, datetime.datetime]:
    date = (datetimeobj - datetime.timedelta(hours=hours))
    return (_prepare_datetime(date), _prepare_datetime(datetimeobj))


def _prepare_datetime(datetimeobj: datetime.datetime) -> str:
    return datetimeobj.astimezone().replace(microsecond=0).isoformat()


def get_bookmark(bookmarks: List, key: str) -> datetime:
    if not bookmarks:
        bookmarks = {}

    bookmark = bookmarks.get(key)
    if not bookmark:
        print(f"bookmark for {key} not found. Creating new bookmark")
        return datetime.datetime.utcnow()

    return parser.parse(bookmark)


if __name__ == '__main__':
    class Request:
        def __init__(self, data) -> None:
            self.data = data

        def get_json(self):
            return self.data

    data = {
        'secrets': 12341234123,
        'state': {
            'bookmarks': {
                'sales': '2021-07-15T23:52:21.879868',
                'inventories': '2021-07-15T23:52:21.879868',
            }
        }
    }

    request = Request(data)
    response = handler(request)
    print(response)
