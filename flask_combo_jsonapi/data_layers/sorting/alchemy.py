"""Helper to create sqlalchemy sortings according to filter querystring parameter"""
from typing import Any, List, Tuple

from sqlalchemy import sql
from sqlalchemy.orm import aliased

from flask_combo_jsonapi.data_layers.shared import create_filters_or_sorts
from flask_combo_jsonapi.exceptions import InvalidFilters, PluginMethodNotImplementedError, InvalidSort
from flask_combo_jsonapi.schema import get_relationships, get_model_field
from flask_combo_jsonapi.utils import SPLIT_REL


Sort = sql.elements.BinaryExpression
Join = List[Any]

SortAndJoins = Tuple[
    Sort,
    List[Join],
]

def create_sorts(model, sort_info, resource):
    """Apply sorts from sorts information to base query

    :param DeclarativeMeta model: the model of the node
    :param list sort_info: current node sort information
    :param Resource resource: the resource
    """
    return create_filters_or_sorts(model, sort_info, resource, Node)


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
        :param str order: desc | asc (or custom)
        :return:
        """
        """
        Custom sqlachemy sorting logic can be created in a marshmallow field for any field
        You can override existing ('asc', 'desc') or create new - then follow this pattern:
        `_<custom_sort_name>_sql_sort_`. This method has to accept following params:
        * marshmallow_field - marshmallow field instance
        * model_column - sqlalchemy column instance
        """
        try:
            f = getattr(marshmallow_field, f'_{order}_sql_sort_')
        except AttributeError:
            pass
        else:
            return f(
                marshmallow_field=marshmallow_field,
                model_column=model_column,
            )
        return getattr(model_column, order)()

    def resolve(self) -> SortAndJoins:
        """Create sort for a particular node of the sort tree"""
        if hasattr(self.resource, 'plugins'):
            for i_plugin in self.resource.plugins:
                try:
                    res = i_plugin.before_data_layers_sorting_alchemy_nested_resolve(self)
                    if res is not None:
                        return res
                except PluginMethodNotImplementedError:
                    pass

        field = self.sort_.get('field', '')
        if not hasattr(self.model, field) and SPLIT_REL not in field:
            raise InvalidSort("{} has no attribute {}".format(self.model.__name__, field))

        if SPLIT_REL in field:
            value = {
                'field': SPLIT_REL.join(field.split(SPLIT_REL)[1:]),
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

        if SPLIT_REL in name:
            name = name.split(SPLIT_REL)[0]

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
