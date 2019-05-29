# -*- coding: utf-8 -*-

import json
from uuid import UUID
from datetime import datetime
import marshmallow
from apispec.ext.marshmallow import resolver
from apispec.ext.marshmallow.common import MODIFIERS
from marshmallow import class_registry


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def create_schema_name(schema=None, name_schema=None):
    if name_schema:
        if name_schema not in class_registry._registry:
            raise ValueError(f'No schema {name_schema}')
        cls_schema = class_registry.get_class(name_schema)
        schema = cls_schema()
    elif schema:
        schema = schema if isinstance(schema, marshmallow.Schema) else schema()
        cls_schema = type(schema)
    if not isinstance(schema, marshmallow.Schema):
        raise TypeError("can only make a schema key based on a Schema instance.")
    modifiers = []
    for modifier in MODIFIERS:
        attribute = getattr(schema, modifier)
        if attribute:
            modifiers.append(f'{modifier}={attribute}')
    modifiers_str = ','.join(modifiers)
    if modifiers_str:
        modifiers_str = f'({modifiers_str})'
    name_cls_schema = resolver(cls_schema)
    return f'{name_cls_schema}{modifiers_str}'
