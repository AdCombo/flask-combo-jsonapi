# -*- coding: utf-8 -*-

"""Helper to create sqlalchemy filters according to filter querystring parameter"""
from typing import Any, List, Tuple

from marshmallow import fields, ValidationError
from sqlalchemy import sql
from sqlalchemy.orm import aliased

from flask_rest_jsonapi.exceptions import InvalidFilters, PluginMethodNotImplementedError
from flask_rest_jsonapi.schema import get_relationships, get_model_field

Sort = sql.elements.BinaryExpression
Join = List[Any]

SortAndJoins = Tuple[
    Sort,
    List[Join]
]

# Список полей, которые немогут быть массивом
STANDARD_MARSHMALLOW_FIELDS = {fields.Dict, fields.Tuple, fields.String, fields.UUID, fields.Number, fields.Integer,
                               fields.Decimal, fields.Boolean, fields.Float, fields.DateTime, fields.LocalDateTime,
                               fields.Date, fields.TimeDelta, fields.Url, fields.Str, fields.Bool, fields.Int,
                               fields.Constant}


def deserialize_field(marshmallow_field: fields.Field, value: Any) -> Any:
    """
    Десериализуем значение, которое приходит в фильтре
    :param marshmallow_field: тип marshmallow поля
    :param value: значение, которое прищло для фильтра
    :return: сериализованное значение
    """
    try:
        if isinstance(value, list) and type(marshmallow_field) in STANDARD_MARSHMALLOW_FIELDS:
            return [marshmallow_field.deserialize(i_value) for i_value in value]
        elif not isinstance(value, list) and isinstance(marshmallow_field, fields.List):
            return marshmallow_field.deserialize([value])
        return marshmallow_field.deserialize(value)
    except ValidationError:
        raise InvalidFilters(f'Bad filter value: {value}')


def create_sorts(model, sort_info, resource):
    """Apply sorts from sorts information to base query

    :param DeclarativeMeta model: the model of the node
    :param list sort_info: current node sort information
    :param Resource resource: the resource
    """
    sorts = []
    joins = []
    for sort_ in sort_info:
        sort, join = Node(model, sort_, resource, resource.schema).resolve()
        sorts.append(sort)
        joins.extend(join)

    return sorts, joins


class Node(object):
    """Helper to recursively create sorts with sqlalchemy according to sort querystring parameter"""

    def __init__(self, model, sort_, resource, schema):
        """Initialize an instance of a filter node

        :param Model model: an sqlalchemy model
        :param dict sort_: sorts information of the current node and deeper nodes
        :param Resource resource: the base resource to apply filters on
        :param Schema schema: the serializer of the resource
        """
        self.model = model
        self.sort_ = sort_
        self.resource = resource
        self.schema = schema

    @classmethod
    def create_sort(cls, marshmallow_field, model_column, order):
        """
        Create sqlalchemy sort
        :param marshmallow_field:
        :param model_column: column sqlalchemy
        :param str order: desc | asc
        :return:
        """
        if hasattr(marshmallow_field, f'_{order}_sql_filter_'):
            """
            У marshmallow field может быть реализована своя логика создания сортировки для sqlalchemy
            для определённого типа ('asc', 'desc'). Чтобы реализовать свою логику создания сортировка для 
            определённого оператора необходимо реализовать в классе поля методы (название метода строится по 
            следующему принципу `_<тип сортировки>_sql_filter_`). Также такой метод должен принимать ряд параметров 
            * marshmallow_field - объект класса поля marshmallow
            * model_column - объект класса поля sqlalchemy
            """
            return getattr(marshmallow_field, f'_{order}_sql_filter_')(
                marshmallow_field=marshmallow_field,
                model_column=model_column
            )
        return getattr(model_column, order)()

    def resolve(self) -> SortAndJoins:
        """Create sort for a particular node of the sort tree"""
        for i_plugins in self.resource.plugins:
            try:
                res = i_plugins.before_data_layers_sorting_alchemy_nested_resolve(self)
                if res is not None:
                    return res
            except PluginMethodNotImplementedError:
                pass

        if '__' in self.sort_.get('field', ''):
            value = {
                'field': '__'.join(self.sort_['field'].split('__')[1:]),
                'order': self.sort_['order']
            }
            alias = aliased(self.related_model)
            joins = [[alias, self.column]]
            node = Node(alias, value, self.resource, self.related_schema)
            filters, new_joins = node.resolve()
            joins.extend(new_joins)
            return filters, joins

        return self.create_sort(
            marshmallow_field=self.schema._declared_fields[self.name],
            model_column=self.column,
            order=self.sort_['order']
        ), []

    @property
    def name(self):
        """Return the name of the node or raise a BadRequest exception

        :return str: the name of the sort to sort on
        """
        name = self.sort_.get('field')

        if name is None:
            raise InvalidFilters("Can't find name of a sort")

        if '__' in name:
            name = name.split('__')[0]

        if name not in self.schema._declared_fields:
            raise InvalidFilters("{} has no attribute {}".format(self.schema.__name__, name))

        return name

    @property
    def column(self):
        """Get the column object

        :param DeclarativeMeta model: the model
        :param str field: the field
        :return InstrumentedAttribute: the column to filter on
        """
        field = self.name

        model_field = get_model_field(self.schema, field)

        try:
            return getattr(self.model, model_field)
        except AttributeError:
            raise InvalidFilters("{} has no attribute {}".format(self.model.__name__, model_field))

    @property
    def related_model(self):
        """Get the related model of a relationship field

        :return DeclarativeMeta: the related model
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            raise InvalidFilters("{} has no relationship attribute {}".format(self.schema.__name__, relationship_field))

        return getattr(self.model, get_model_field(self.schema, relationship_field)).property.mapper.class_

    @property
    def related_schema(self):
        """Get the related schema of a relationship field

        :return Schema: the related schema
        """
        relationship_field = self.name

        if relationship_field not in get_relationships(self.schema):
            raise InvalidFilters("{} has no relationship attribute {}".format(self.schema.__name__, relationship_field))

        return self.schema._declared_fields[relationship_field].schema.__class__
