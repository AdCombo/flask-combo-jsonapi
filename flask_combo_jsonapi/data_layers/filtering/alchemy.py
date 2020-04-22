"""Helper to create sqlalchemy filters according to filter querystring parameter"""
from typing import Any, List, Tuple

from sqlalchemy import and_, or_, not_, sql
from sqlalchemy.orm import aliased

from flask_combo_jsonapi.data_layers.shared import deserialize_field, create_filters_or_sorts
from flask_combo_jsonapi.exceptions import InvalidFilters, PluginMethodNotImplementedError
from flask_combo_jsonapi.schema import get_relationships, get_model_field
from flask_combo_jsonapi.utils import SPLIT_REL


Filter = sql.elements.BinaryExpression
Join = List[Any]

FilterAndJoins = Tuple[
    Filter,
    List[Join],
]


def create_filters(model, filter_info, resource):
    """Apply filters from filters information to base query

    :param DeclarativeMeta model: the model of the node
    :param dict filter_info: current node filter information
    :param Resource resource: the resource
    """
    return create_filters_or_sorts(model, filter_info, resource, Node)


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
        """
        Custom sqlachemy filtering logic can be created in a marshmallow field for any operator
        To implement a new filtering logic (override existing or create a new one)
        create a method inside a field following this pattern:
        `_<your_op_name>_sql_filter_`. Each filtering method has to accept these params: 
        * marshmallow_field - marshmallow field instance
        * model_column - sqlalchemy column instance
        * value - filtering value
        * operator - your operator, for example: "eq", "in", "ilike_str_array", ...
        """
        try:
            f = getattr(marshmallow_field, f'_{operator}_sql_filter_')
        except AttributeError:
            pass
        else:
            return f(
                marshmallow_field=marshmallow_field,
                model_column=model_column,
                value=value,
                operator=operator,
            )
        # Here we have to deserialize and validate fields, that are used in filtering,
        # so the Enum fields are loaded correctly
        value = deserialize_field(marshmallow_field, value)
        return getattr(model_column, self.operator)(value)

    def resolve(self) -> FilterAndJoins:
        """Create filter for a particular node of the filter tree"""
        if self.resource and hasattr(self.resource, 'plugins'):
            for i_plugin in self.resource.plugins:
                try:
                    res = i_plugin.before_data_layers_filtering_alchemy_nested_resolve(self)
                    if res is not None:
                        return res
                except PluginMethodNotImplementedError:
                    pass

        if all(map(
                lambda op: op not in self.filter_,
                ('or', 'and', 'not'),
        )):
            value = self.value

            if isinstance(value, dict):
                alias = aliased(self.related_model)
                joins = [[alias, self.column]]
                filters, new_joins = Node(self.related_model, value, self.resource, self.related_schema).resolve()

                joins.extend(new_joins)
                return filters, joins

            if SPLIT_REL in self.filter_.get('name', ''):
                value = {
                    'name': SPLIT_REL.join(self.filter_['name'].split(SPLIT_REL)[1:]),
                    'op': self.filter_['op'],
                    'val': value,
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
                value=value,
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

        if SPLIT_REL in name:
            name = name.split(SPLIT_REL)[0]

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
