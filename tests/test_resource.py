from unittest.mock import Mock

import pytest
from marshmallow_jsonapi import fields, Schema
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from flask_combo_jsonapi import ResourceList


@pytest.fixture(scope='module')
def base():
    yield declarative_base()


@pytest.fixture(scope='module')
def model(base):
    class SampleModel(base):
        __tablename__ = 'model_sample'

        id = Column(Integer, primary_key=True, index=True)
        key1 = Column(String)
        key2 = Column(String)

        def __init__(self, key1):
            pass

    yield SampleModel


@pytest.fixture(scope='module')
def schema_for_model(model):
    class SampleSchema(Schema):
        class Meta:
            model = model

        id = fields.Integer()
        key1 = fields.String()
        key2 = fields.String()

    yield SampleSchema


def test_resource_meta_init(model, schema_for_model):
    expected_fields = ['id', 'key2']
    raised_ex = None
    try:
        class SampleResourceList(ResourceList):
            schema = schema_for_model
            methods = ['GET', 'POST']
            data_layer = {
                'session': Mock(),
                'model': model,
            }
    except Exception as ex:
        raised_ex = ex

    assert raised_ex
    message = f"Construction of SampleResourceList failed. Schema '{schema_for_model.__name__}' " \
              f"has fields={expected_fields}"
    assert message in str(raised_ex)
