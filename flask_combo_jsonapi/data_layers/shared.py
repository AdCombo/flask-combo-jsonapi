from typing import Any

from marshmallow import fields, ValidationError

from flask_combo_jsonapi.exceptions import InvalidFilters


# Fields that are not of array type
STANDARD_MARSHMALLOW_FIELDS = {
    fields.Dict,
    fields.Tuple,
    fields.String,
    fields.UUID,
    fields.Number,
    fields.Integer,
    fields.Decimal,
    fields.Boolean,
    fields.Float,
    fields.DateTime,
    fields.Date,
    fields.TimeDelta,
    fields.Url,
    fields.Str,
    fields.Bool,
    fields.Int,
    fields.Constant,
}


def deserialize_field(marshmallow_field: fields.Field, value: Any) -> Any:
    """
    Deserialize filter/sort value
    :param marshmallow_field: marshmallow field type
    :param value: filter/sort value
    :return:
    """
    try:
        if isinstance(value, list) and type(marshmallow_field) in STANDARD_MARSHMALLOW_FIELDS:
            return [marshmallow_field.deserialize(i_value) for i_value in value]
        if not isinstance(value, list) and isinstance(marshmallow_field, fields.List):
            return marshmallow_field.deserialize([value])
        return marshmallow_field.deserialize(value)
    except ValidationError:
        raise InvalidFilters(f'Bad filter value: {value!r}')


def create_filters_or_sorts(model, filter_or_sort_info, resource, Node):
    """
    Apply filters / sorts from filters / sorts information to base query

    :param DeclarativeMeta model: the model of the node
    :param dict/list filter_or_sort_info: current node filter_or_sort information
    :param Node:
    :param Resource resource: the resource
    """
    filters_or_sorts = []
    joins = []
    schema = getattr(resource, 'schema') if resource else None
    for filter_or_sort in filter_or_sort_info:
        filters_or_sort, join = Node(model, filter_or_sort, resource, schema).resolve()
        filters_or_sorts.append(filters_or_sort)
        joins.extend(join)

    return filters_or_sorts, joins
