import requests

class RakutenClientError(Exception):
    def __init__(self, message=None, response=None):
        super().__init__(message)
        self.message = message
        self.response = response


class RakutenClient9001Error(RakutenClientError):
    pass


class RakutenClient9003Error(RakutenClientError):
    pass


class RakutenClient9066Error(RakutenClientError):
    pass


class RakutenClient9067Error(RakutenClientError):
    pass


class RakutenClient9068Error(RakutenClientError):
    pass


class RakutenClient9069Error(RakutenClientError):
    pass


class RakutenClient9099Error(RakutenClientError):
    pass


class RakutenClient1003Error(RakutenClientError):
    pass


class RakutenClient1009Error(RakutenClientError):
    pass


class RakutenClient1043Error(RakutenClientError):
    pass


class RakutenClient1092Error(RakutenClientError):
    pass


ERROR_CODE_EXCEPTION_MAPPING = {
    9001: {
        'raise_exception': RakutenClient9001Error,
        'message': 'Field is null or empty.',
    },
    9003: {
        'raise_exception': RakutenClient9003Error,
        'message': 'Field length exceeded.'
    },
    9066: {
        'raise_exception': RakutenClient9066Error,
        'message': 'API credential does not exist.'
    },
    9067: {
        'raise_exception': RakutenClient9067Error,
        'message': 'API credential is invalid.'
    },
    9068: {
        'raise_exception': RakutenClient9068Error,
        'message': 'API credential is expired.'
    },
    9069: {
        'raise_exception': RakutenClient9069Error,
        'message': 'API credential is disabled.'
    },
    9099: {
        'raise_exception': RakutenClient9099Error,
        'message': 'Field should be a number greater than zero.'
    },
    1003: {
        'raise_exception': RakutenClient1003Error,
        'message': 'Field length exceeded.'
    },
    1009: {
        'raise_exception': RakutenClient1009Error,
        'message': 'Stock Keeping Unit not found.'
    },
    1043: {
        'raise_exception': RakutenClient1043Error,
        'message': 'Field contains restricted characters.'
    },
    1092: {
        'raise_exception': RakutenClient1092Error,
        'message': 'Field should be the number in the specified range.'
    },
}


def raise_for_error(resp):
    try:
        resp.raise_for_status()
    except (requests.HTTPError, requests.ConnectionError) as error:
        try:
            error_code = resp.status_code
            client_exception = ERROR_CODE_EXCEPTION_MAPPING.get(error_code, {})
            exc = client_exception.get('raise_exception', RakutenClientError)
            message = client_exception.get('message', 'Client Error')

            raise exc(message, resp) from None

        except (ValueError, TypeError):
            raise RakutenClientError(error) from None