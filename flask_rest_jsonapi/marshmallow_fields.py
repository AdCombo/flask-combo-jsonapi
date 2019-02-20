from marshmallow import fields
from marshmallow_jsonapi.fields import Relationship as OldRelationship


class Relationship(fields.Nested, OldRelationship):
    """Данное поле нужно, чтобы в apispec в openapi строился json ссылающиеся на другую схему, а
    для этого необходимо, чтобы поле было унаследованно от fields.Nested, всё отличие от Relationship из
    marshmallow_jsonapi.fields в том что первым аргументом при создание объекта нужно передавать схему,
    на которую будет ссылаться поле"""
