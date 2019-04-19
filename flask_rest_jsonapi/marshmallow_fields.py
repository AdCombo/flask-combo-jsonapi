from copy import deepcopy

from marshmallow import fields
from marshmallow_jsonapi.fields import Relationship as OldRelationship

delattr(fields.Nested, 'schema')


class Relationship(OldRelationship, fields.Nested):
    """Данное поле нужно, чтобы в apispec в openapi строился json ссылающиеся на другую схему, а
    для этого необходимо, чтобы поле было унаследованно от fields.Nested, всё отличие от Relationship из
    marshmallow_jsonapi.fields в том что первым аргументом при создание объекта нужно передавать схему,
    на которую будет ссылаться поле"""

    def __init__(self, **kwargs):
        OldRelationship.__init__(self, **deepcopy(kwargs))
        fields.Nested.__init__(self, **kwargs)

    def deserialize(self, value, attr=None, data=None, **kwargs):
        return super(OldRelationship, self).deserialize(value, attr, data)
