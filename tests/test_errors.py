from unittest.mock import Mock

from flask_combo_jsonapi import JsonApiException
from flask_combo_jsonapi.errors import format_http_exception


def test_format_http_exception__value_error():
    ex = Mock()
    ex.code = 'f405'

    assert format_http_exception(ex) is None


def test_format_http_exception__type_error():
    ex = Mock()
    ex.code = 'not_int'

    assert format_http_exception(ex) is None


def test_format_http_exception__success():
    ex = Mock()
    ex.code = 400

    res = format_http_exception(ex)

    assert isinstance(res, JsonApiException)
    assert res.status == '400'
