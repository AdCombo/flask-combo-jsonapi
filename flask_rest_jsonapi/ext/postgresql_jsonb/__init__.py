import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import cast, String, Integer, Boolean, DECIMAL
from sqlalchemy.sql.elements import or_

from flask_rest_jsonapi.data_layers.filtering.alchemy import deserialize_field
from marshmallow import Schema, fields as ma_fields

from flask_rest_jsonapi.exceptions import InvalidFilters
from flask_rest_jsonapi.ext.postgresql_jsonb.schema import SchemaJSONB
from flask_rest_jsonapi.marshmallow_fields import Relationship
from flask_rest_jsonapi.plugin import BasePlugin


def is_seq_collection(obj):
    """
    является ли переданный объект set, list, tuple
    :param obj:
    :return bool:
    """
    return isinstance(obj, (list, set, tuple))


class PostgreSqlJSONB(BasePlugin):

    def before_data_layers_filtering_alchemy_nested_resolve(self, self_nested: Any) -> Any:
        """
        Проверяем, если фильтр по jsonb полю, то создаём фильтр и возвращаем результат,
        если фильтр по другому полю, то возвращаем None
        :param self_nested:
        :return:
        """
        if not ({'or', 'and', 'not'} & set(self_nested.filter_)):

            if '__' in self_nested.filter_.get('name', ''):
                if self._isinstance_jsonb(self_nested.schema, self_nested.filter_['name']):
                    filter = self._create_filter(
                        self_nested,
                        marshmallow_field=self_nested.schema._declared_fields[self_nested.name],
                        model_column=self_nested.column,
                        operator=self_nested.filter_['op'],
                        value=self_nested.value
                    )
                    return filter, []

    @classmethod
    def _isinstance_jsonb(cls, schema: Schema, filter_name):
        """
        Определяем относится ли фильтр к relationship или к полю JSONB
        :param schema:
        :param fields:
        :return:
        """
        fields = filter_name.split('__')
        for i, i_field in enumerate(fields):
            if isinstance(getattr(schema._declared_fields[i_field], 'schema', None), SchemaJSONB):
                if i != (len(fields) - 2):
                    raise InvalidFilters(f'Invalid JSONB filter: {filter_name}')
                return True
            elif isinstance(schema._declared_fields[i_field], Relationship):
                schema = schema._declared_fields[i_field].schema
            else:
                return False
        return False

    @classmethod
    def _create_filter(cls, self_nested: Any, marshmallow_field, model_column, operator, value):
        """
        Create sqlalchemy filter
        :param Nested self_nested:
        :param marshmallow_field:
        :param model_column: column sqlalchemy
        :param operator:
        :param value:
        :return:
        """
        fields = self_nested.filter_['name'].split('__')
        self_nested.filter_['name'] = '__'.join(fields[:-1])
        field_in_jsonb = fields[-1]

        if not isinstance(getattr(marshmallow_field, 'schema', None), SchemaJSONB):
            raise InvalidFilters(f'Invalid JSONB filter: {"__".join(self_nested.fields)}')
        marshmallow_field = marshmallow_field.schema._declared_fields[field_in_jsonb]
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
                model_column=model_column.op('->>')(field_in_jsonb),
                value=value,
                operator=self_nested.operator
            )
        mapping = {v: k for k, v in self_nested.schema.TYPE_MAPPING.items()}
        mapping[ma_fields.Email] = str
        mapping[ma_fields.Dict] = dict
        mapping[ma_fields.List] = list
        mapping[ma_fields.Decimal] = Decimal
        mapping[ma_fields.Url] = str
        mapping[ma_fields.LocalDateTime] = datetime.datetime

        # Нужно проводить валидацию и делать десериализацию значение указанных в фильтре, так как поля Enum
        # например выгружаются как 'name_value(str)', а в БД хранится как просто число
        value = deserialize_field(marshmallow_field, value)

        property_type = mapping[type(marshmallow_field)]
        extra_field = model_column.op('->>')(field_in_jsonb)
        filter = ''
        if property_type == Decimal:
            filter = getattr(cast(extra_field, DECIMAL), self_nested.operator)(value)

        if property_type in {str, bytes}:
            filter = getattr(cast(extra_field, String), self_nested.operator)(value)

        if property_type == int:
            field = cast(extra_field, Integer)
            if value:
                filter = getattr(field, self_nested.operator)(value)
            else:
                filter = or_(getattr(field, self_nested.operator)(value), field.is_(None))

        if property_type == bool:
            filter = (cast(extra_field, Boolean) == value)

        if property_type == list:
            filter = model_column.op('->')(field_in_jsonb).op('?')(value[0] if is_seq_collection(value) else value)

        return filter
