"""Helper to  format Api errors according to jsonapi specification"""
from flask_combo_jsonapi.exceptions import BadRequest, ObjectNotFound, InvalidType, AccessDenied, Unauthorized

STATUS_MAP = {
    400: BadRequest,
    401: Unauthorized,
    404: ObjectNotFound,
    409: InvalidType,
    403: AccessDenied,
}


def jsonapi_errors(jsonapi_errors):
    """Construct api error according to jsonapi 1.0

    :param iterable jsonapi_errors: an iterable of jsonapi error
    :return dict: a dict of errors according to jsonapi 1.0
    """
    return {'errors': [jsonapi_error for jsonapi_error in jsonapi_errors],
            'jsonapi': {'version': '1.0'}}


def format_http_exception(ex):
    """
    try to format http exception to jsonapi 1.0
    Warning! It only works for errors with status code less than 500
    :param ex: http exception
    :return:
    """
    code = getattr(ex, 'code', None)
    try:
        status = int(code)
    except (TypeError, ValueError):
        return

    api_ex = STATUS_MAP.get(status)
    if not api_ex:
        return

    return api_ex(detail=getattr(ex, 'description', ''))
