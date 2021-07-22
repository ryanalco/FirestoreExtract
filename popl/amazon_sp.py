import datetime
import json
from enum import Enum
from typing import List, Tuple

import backoff
from dateutil import parser
from sp_api.api import Inventories, Sales
from sp_api.base.exceptions import (SellingApiRequestThrottledException,
                                    SellingApiServerException,
                                    SellingApiTemporarilyUnavailableException)
from sp_api.base.sales_enum import Granularity


def amazon_sp_handler(request):
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
    now = datetime.datetime.utcnow()

    state = {
        'bookmarks': {
            'sales': now.isoformat(),
            'inventories': now.isoformat(),
        }
    }

    insert = {
        "sales": get_sales(sales_bookmark, now),
        "inventories": get_inventories(inventories_bookmark)
    }

    return assemble_response_json(insert, state), 200, {"Content-Type": "application/json"}


def log_backoff(details):
    '''
    Logs a backoff retry message
    '''
    print(f'Error receiving data from Amazon SP API. Sleeping {details["wait"]:.1f} seconds before trying again')


def get_inventories(datetimeobj: datetime.datetime) -> List:
    """Get inventories data.
    Docs: https://github.com/amzn/selling-partner-api-docs/blob/main/references/fba-inventory-api/fbaInventory.md#getinventorysummariesresponse
    """
    print("getting inventories data...")
    start_date_time = datetimeobj.isoformat()

    return _get_inventories(start_date_time)


@backoff.on_exception(backoff.expo,
                     (SellingApiRequestThrottledException,
                      SellingApiServerException,
                      SellingApiTemporarilyUnavailableException),
                      max_tries=3,
                      on_backoff=log_backoff)
def _get_inventories(start_date_time: str) -> List:
    client = Inventories()
    response = client.get_inventory_summary_marketplace(startDateTime=start_date_time)

    return response.payload['inventorySummaries']


def get_sales(start_date: datetime.datetime, end_date: datetime.datetime) -> List:
    """Get aggregated sales info.
    Docs: https://github.com/amzn/selling-partner-api-docs/blob/8438231aefe8dfbdf7c1758ddf137a0c728bb21b/references/sales-api/sales.md#getordermetricsresponse
    """

    print("getting sales data...")
    interval = create_date_interval(start_date, end_date)

    return _get_sales(interval, Granularity.HOUR)


@backoff.on_exception(backoff.expo,
                     (SellingApiRequestThrottledException,
                      SellingApiServerException,
                      SellingApiTemporarilyUnavailableException),
                      max_tries=3,
                      on_backoff=log_backoff)
def _get_sales(interval: Tuple, granularity: Enum) -> List:
    client = Sales()
    response = client.get_order_metrics(interval=interval, granularity=granularity)

    return response.payload


def assemble_response_json(insert, state):
    response_dict = {
        "state": state,
        "schema": {
            "inventories": {
                "primary_key": [
                    "asin",
                    "fnSku",
                    "sellerSku",
                    "lastUpdatedTime"
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


def create_date_interval(start_date: datetime.datetime,
                         end_date: datetime.datetime,
                         hours=1) -> Tuple[datetime.datetime, datetime.datetime]:
    date = (start_date - datetime.timedelta(hours=hours))
    return (_prepare_datetime(date), _prepare_datetime(end_date))


def _prepare_datetime(datetimeobj: datetime.datetime) -> str:
    return datetimeobj.astimezone().replace(microsecond=0).isoformat()


def get_bookmark(bookmarks: List, key: str) -> datetime.datetime:
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
        "secrets": 12341234123,
        "state": {
            "bookmarks": {
                "sales": "2021-07-15T23:52:21.879868",
                "inventories": "2021-07-15T23:52:21.879868"
            }
        }
    }

    request = Request(data)
    response = amazon_sp_handler(request)
    print(response)