import pytest

from flask import Flask


@pytest.fixture()
def app():
    app = Flask(__name__)
    return app


@pytest.yield_fixture()
def client(app):
    return app.test_client()
