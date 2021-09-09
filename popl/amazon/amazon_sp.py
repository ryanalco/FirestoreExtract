import datetime
import json
import time
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
    now = datetime.datetime.utcnow()

    state = {
        'bookmarks': {
            'sales': now.isoformat(),
            'inventories': now.isoformat(),
        }
    }

    inventories, seller_skus = get_inventories()

    insert = {
        "sales": get_sales(sales_bookmark, now, seller_skus),
        "inventories": inventories
    }

    return assemble_response_json(insert, state), 200, {"Content-Type": "application/json"}


def log_backoff(details):
    '''
    Logs a backoff retry message
    '''
    print(f'Error receiving data from Amazon SP API. Sleeping {details["wait"]:.1f} seconds before trying again')


@backoff.on_exception(backoff.expo,
                     (SellingApiRequestThrottledException,
                      SellingApiServerException,
                      SellingApiTemporarilyUnavailableException),
                      max_tries=3,
                      on_backoff=log_backoff)
def get_inventories() -> Tuple[List, List]:
    client = Inventories()
    paginate = True
    next_token = None
    seller_skus = set()
    payload = []

    while paginate:
        response = client.get_inventory_summary_marketplace(details=True, nextToken=next_token)
        seller_skus = seller_skus.union(get_seller_skus(response.payload['inventorySummaries']))
        if response.pagination:
            next_token = response.pagination.get("nextToken")
        else:
            next_token = None
        paginate = True if next_token else False
        payload.extend(response.payload['inventorySummaries'])

    return (payload, seller_skus)


def get_sales(start_date: datetime.datetime, end_date: datetime.datetime, seller_skus: set) -> List:
    """Get aggregated sales info.
    Docs: https://github.com/amzn/selling-partner-api-docs/blob/8438231aefe8dfbdf7c1758ddf137a0c728bb21b/references/sales-api/sales.md#getordermetricsresponse
    """

    print("getting sales data...")
    interval = create_date_interval(start_date, end_date)

    return _get_sales(interval, Granularity.HOUR, seller_skus)


@backoff.on_exception(backoff.expo,
                     (SellingApiRequestThrottledException,
                      SellingApiServerException,
                      SellingApiTemporarilyUnavailableException),
                      max_tries=3,
                      on_backoff=log_backoff)
def _get_sales(interval: Tuple, granularity: Enum, seller_skus: List) -> List:
    client = Sales()

    records = []
    num_seller_skus = len(seller_skus)
    for idx, sku in enumerate(seller_skus, start=1):
        if not sku:
            continue
        print(f"Getting sales data for sellerSku: {sku} ({idx}/{num_seller_skus})")
        response = client.get_order_metrics(interval=interval, granularity=granularity, sku=sku)

        for record in response.payload:
            record.update({'sellerSku': sku})
            records.append(record)

        sleep_time = 2
        print(f"response:\n\t {json.dumps(response.payload, indent=2)}")
        print("=" * 120)
        print(f"Sleeping for {sleep_time} seconds...")
        time.sleep(sleep_time)

    return records


def assemble_response_json(insert, state):
    response_dict = {
        "state": state,
        "schema": {
            "inventories": {
                "primary_key": [
                    "asin",
                    "fnSku",
                    "sellerSku",
                ]
            },
            "sales": {
                "primary_key": [
                    "interval",
                    "sellerSku"
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


def get_seller_skus(payload: List) -> set:
    return {record.get('sellerSku') for record in payload}


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
                "sales": "2021-07-27T16:52:21.879868",
                "inventories": "2021-07-27T16:52:21.879868"
            }
        }
    }

    request = Request(data)
    response = amazon_sp_handler(request)
    print(response)
