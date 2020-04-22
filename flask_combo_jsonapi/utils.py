import inspect

import simplejson as json
from uuid import UUID
from datetime import datetime


"""
Splitter for filters, sorts and includes
Previously used: '__'
"""
SPLIT_REL = '.'


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def get_model_init_params_names(model):
    """Retrieve all params of model init method

    :param DeclarativeMeta model: an object from sqlalchemy
    :return tuple: list of init method fields names and boolean flag that init method has kwargs
    """
    argnames, _, varkw = inspect.getfullargspec(model.__init__)[:3]
    if argnames:
        argnames.remove('self')
    return argnames, bool(varkw)


def validate_model_init_params(model, params_names):
    """Retrieve invalid params of model init method if it exists
    :param DeclarativeMeta model: an object from sqlalchemy
    :param list params_names: parameters names to check
    :return list: list of invalid fields or None
    """
    init_args, has_kwargs = get_model_init_params_names(model)
    if has_kwargs:
        return

    invalid_params = [name for name in params_names if name not in init_args]
    if invalid_params:
        return invalid_params
