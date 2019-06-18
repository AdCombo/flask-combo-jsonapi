# -*- coding: utf-8 -*-

"""Helper to create sqlalchemy filters according to filter querystring parameter"""
from typing import Any, List, Tuple

from marshmallow import fields, ValidationError
from sqlalchemy import and_, or_, not_, sql
from sqlalchemy.orm import aliased

from flask_rest_jsonapi.exceptions import InvalidFilters, PluginMethodNotImplementedError
from flask_rest_jsonapi.schema import get_relationships, get_model_field

Filter = sql.elements.BinaryExpression
Join = List[Any]

FilterAndJoins = Tuple[
    Filter,
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


def create_filters(model, filter_info, resource):
    """Apply filters from filters information to base query

    :param DeclarativeMeta model: the model of the node
    :param dict filter_info: current node filter information
    :param Resource resource: the resource
    """
    filters = []
    joins = []
    for filter_ in filter_info:
        # filters.append(Node(model, filter_, resource, resource.schema).resolve())
        filter, join = Node(model, filter_, resource, resource.schema).resolve()
        filters.append(filter)
        joins.extend(join)

    return filters, joins


class Node(object):
    """Helper to recursively create filters with sqlalchemy according to filter querystring parameter"""

    def __init__(self, model, filter_, resource, schema):
        """Initialize an instance of a filter node

        :param Model model: an sqlalchemy model
        :param dict filter_: filters information of the current node and deeper nodes
        :param Resource resource: the base resource to apply filters on
        :param Schema schema: the serializer of the resource
        """
        self.model = model
        self.filter_ = filter_
        self.resource = resource
        self.schema = schema

    def create_filter(self, marshmallow_field, model_column, operator, value):
        """
        Create sqlalchemy filter
        :param marshmallow_field:
        :param model_column: column sqlalchemy
        :param operator:
        :param value:
        :return:
        """
        if hasattr(marshmallow_field, f'_{operator}_sql_filter_'):
            """
            У marshmallow field может быть реализована своя логика создания фильтра для sqlalchemy
            для определённого оператора. Чтобы реализовать свою логику создания фильтра для определённого оператора
            необходимо реализовать в классе поля методы (название метода строится по следующему принципу
            `_<тип оператора>_sql_filter_`). Также такой метод должен принимать ряд параметров 
            * marshmallow_field - объект класса поля marshmallow
            * model_column - объект класса поля sqlalchemy
            * value - значения для фильтра
            * operator - сам оператор, например: "eq", "in"...
            """
            return getattr(marshmallow_field, f'_{operator}_sql_filter_')(
                marshmallow_field=marshmallow_field,
                model_column=model_column,
                value=value,
                operator=self.operator
            )
        # Нужно проводить валидацию и делать десериализацию значение указанных в фильтре, так как поля Enum
        # например выгружаются как 'name_value(str)', а в БД хранится как просто число
        value = deserialize_field(marshmallow_field, value)
        return getattr(model_column, self.operator)(value)

    def resolve(self) -> FilterAndJoins:
        """Create filter for a particular node of the filter tree"""
        for i_plugins in self.resource.plugins:
            try:
                res = i_plugins.before_data_layers_filtering_alchemy_nested_resolve(self)
                if res is not None:
                    return res
            except PluginMethodNotImplementedError:
                pass
        if 'or' not in self.filter_ and 'and' not in self.filter_ and 'not' not in self.filter_:
            value = self.value

            if isinstance(value, dict):
                alias = aliased(self.related_model)
                joins = [[alias, self.column]]
                filters, new_joins = Node(self.related_model, value, self.resource, self.related_schema).resolve()

                joins.extend(new_joins)
                return filters, joins

            if '__' in self.filter_.get('name', ''):
                value = {
                    'name': '__'.join(self.filter_['name'].split('__')[1:]),
                    'op': self.filter_['op'],
                    'val': value
                }
                alias = aliased(self.related_model)
                joins = [[alias, self.column]]
                node = Node(alias, value, self.resource, self.related_schema)
                filters, new_joins = node.resolve()
                joins.extend(new_joins)
                return filters, joins

            return self.create_filter(
                marshmallow_field=self.schema._declared_fields[self.name],
                model_column=self.column,
                operator=self.filter_['op'],
                value=value
            ), []

        if 'or' in self.filter_:
            return self._create_filters(type_filter='or')
        if 'and' in self.filter_:
            return self._create_filters(type_filter='and')
        if 'not' in self.filter_:
            filter, joins = Node(self.model, self.filter_['not'], self.resource, self.schema).resolve()
            return not_(filter), joins

    def _create_filters(self, type_filter: str) -> FilterAndJoins:
        """
        Создаём  фильтр or или and
        :param type_filter: 'or' или 'and'
        :return:
        """
        nodes = [Node(self.model, filter, self.resource, self.schema).resolve() for filter in self.filter_[type_filter]]
        joins = []
        for i_node in nodes:
            joins.extend(i_node[1])
        op = and_ if type_filter == 'and' else or_
        return op(*[i_node[0] for i_node in nodes]), joins

    @property
    def name(self):
        """Return the name of the node or raise a BadRequest exception

        :return str: the name of the field to filter on
        """
        name = self.filter_.get('name')

        if name is None:
            raise InvalidFilters("Can't find name of a filter")

        if '__' in name:
            name = name.split('__')[0]

        if name not in self.schema._declared_fields:
            raise InvalidFilters("{} has no attribute {}".format(self.schema.__name__, name))

        return name

    @property
    def op(self):
        """Return the operator of the node

        :return str: the operator to use in the filter
        """
        try:
            return self.filter_['op']
        except KeyError:
            raise InvalidFilters("Can't find op of a filter")

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
    def operator(self):
        """Get the function operator from his name

        :return callable: a callable to make operation on a column
        """
        operators = (self.op, self.op + '_', '__' + self.op + '__')

        for op in operators:
            if hasattr(self.column, op):
                return op

        raise InvalidFilters("{} has no operator {}".format(self.column.key, self.op))

    @property
    def value(self):
        """Get the value to filter on

        :return: the value to filter on
        """
        if self.filter_.get('field') is not None:
            try:
                result = getattr(self.model, self.filter_['field'])
            except AttributeError:
                raise InvalidFilters("{} has no attribute {}".format(self.model.__name__, self.filter_['field']))
            else:
                return result
        else:
            if 'val' not in self.filter_:
                raise InvalidFilters("Can't find value or field in a filter")

            return self.filter_['val']

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
