import pytest

from flask import Flask


@pytest.fixture(scope="session")
def app():
    app = Flask(__name__)
    return app


@pytest.yield_fixture(scope="session")
def client(app):
    return app.test_client()
