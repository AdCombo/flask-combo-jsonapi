from copy import deepcopy

from marshmallow import fields, class_registry, ValidationError
from marshmallow.base import SchemaABC
from marshmallow_jsonapi.compat import basestring
from marshmallow_jsonapi.fields import Relationship as OldRelationship
from marshmallow.utils import is_collection, missing as missing_

_RECURSIVE_NESTED = 'self'


class Relationship(OldRelationship, fields.Nested):
    """Данное поле нужно, чтобы в apispec в openapi строился json ссылающиеся на другую схему, а
    для этого необходимо, чтобы поле было унаследованно от fields.Nested, всё отличие от Relationship из
    marshmallow_jsonapi.fields в том что первым аргументом при создание объекта нужно передавать схему,
    на которую будет ссылаться поле"""

    def __init__(self, **kwargs):
        OldRelationship.__init__(self, **deepcopy(kwargs))
        fields.Nested.__init__(self, **kwargs)

    @property
    def schema(self):
        only = getattr(self, 'only', None)
        exclude = getattr(self, 'exclude', ())
        context = getattr(self, 'context', {})

        if isinstance(self.__schema, SchemaABC):
            return self.__schema
        if isinstance(self.__schema, type) and issubclass(self.__schema, SchemaABC):
            self.__schema = self.__schema(only=only, exclude=exclude, context=context)
            return self.__schema
        if isinstance(self.__schema, basestring):
            if self.__schema == _RECURSIVE_NESTED:
                parent_class = self.parent.__class__
                self.__schema = parent_class(
                    only=only, exclude=exclude, context=context,
                    include_data=self.parent.include_data,
                )
            else:
                schema_class = class_registry.get_class(self.__schema)
                self.__schema = schema_class(
                    only=only, exclude=exclude,
                    context=context,
                )
            return self.__schema
        else:
            raise ValueError((
                'A Schema is required to serialize a nested '
                'relationship with include_data'
            ))

    def deserialize(self, value, attr=None, data=None, **kwargs):
        """Deserialize ``value``.

        :raise ValidationError: If the value is not type `dict`, if the
            value does not contain a `data` key, and if the value is
            required but unspecified.
        """
        if value is missing_:
            return super(OldRelationship, self).deserialize(value, attr, data)
        if not isinstance(value, dict) or 'data' not in value:
            # a relationships object does not need 'data' if 'links' is present
            if value and 'links' in value:
                return missing_
            else:
                raise ValidationError('Must include a `data` key')
        return super(OldRelationship, self).deserialize(value['data'], attr, data)

    def _deserialize(self, value, attr, obj):
        if self.many:
            if not is_collection(value):
                raise ValidationError('Relationship is list-like')
            return [self.extract_value(item) for item in value]

        if is_collection(value):
            raise ValidationError('Relationship is not list-like')
        return self.extract_value(value)

    def _serialize(self, value, attr, obj):
        dict_class = self.parent.dict_class if self.parent else dict

        ret = dict_class()
        self_url = self.get_self_url(obj)
        related_url = self.get_related_url(obj)
        if self_url or related_url:
            ret['links'] = dict_class()
            if self_url:
                ret['links']['self'] = self_url
            if related_url:
                ret['links']['related'] = related_url

        # resource linkage is required when including the data
        if self.include_resource_linkage or self.include_data:
            if value is None:
                ret['data'] = [] if self.many else None
            else:
                ret['data'] = self.get_resource_linkage(value)

        if self.include_data and value is not None:
            if self.many:
                for item in value:
                    self._serialize_included(item)
            else:
                self._serialize_included(value)
        return ret
