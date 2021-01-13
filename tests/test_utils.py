import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from flask_combo_jsonapi.utils import get_model_init_params_names, validate_model_init_params


@pytest.fixture(scope='module')
def base():
    yield declarative_base()


@pytest.fixture(scope='module')
def model_without_init(base):
    class ModelWithoutInit(base):
        __tablename__ = 'model_without_init'

        id = Column(Integer, primary_key=True, index=True)
        key1 = Column(String)
        key2 = Column(String)

    yield ModelWithoutInit


@pytest.fixture(scope='module')
def model_with_kwargs_in_init(base):
    class ModelWithKwargsInit(base):
        __tablename__ = 'model_with_kwargs_init'

        id = Column(Integer, primary_key=True, index=True)
        key1 = Column(String)
        key2 = Column(String)

        def __init__(self, key1=0, **kwargs):
            pass

    yield ModelWithKwargsInit


@pytest.fixture(scope='module')
def model_with_positional_args_init(base):
    class ModelWithPositionalArgsInit(base):
        __tablename__ = 'model_with_positional_args_init'

        id = Column(Integer, primary_key=True, index=True)
        key1 = Column(String)
        key2 = Column(String)

        def __init__(self, key1, key2=0):
            pass

    yield ModelWithPositionalArgsInit


def test_get_model_init_params_names(model_without_init, model_with_kwargs_in_init,
                                     model_with_positional_args_init):
    args, has_kwargs = get_model_init_params_names(model_without_init)
    assert ([], True) == (args, has_kwargs)

    args, has_kwargs = get_model_init_params_names(model_with_kwargs_in_init)
    assert (['key1'], True) == (args, has_kwargs)

    args, has_kwargs = get_model_init_params_names(model_with_positional_args_init)
    assert (['key1', 'key2'], False) == (args, has_kwargs)


def test_validate_model_init_params(model_with_kwargs_in_init, model_with_positional_args_init):
    schema_attrs = ['id', 'key1', 'key2']
    invalid_params = validate_model_init_params(model_with_kwargs_in_init, schema_attrs)
    assert invalid_params is None

    invalid_params = validate_model_init_params(model_with_positional_args_init, schema_attrs)
    assert invalid_params == ['id']
