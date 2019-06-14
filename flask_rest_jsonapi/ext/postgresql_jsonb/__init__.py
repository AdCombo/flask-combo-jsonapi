import json

from flask_rest_jsonapi.exceptions import InvalidFilters
from marshmallow import Schema
from werkzeug.datastructures import ImmutableMultiDict

from flask_rest_jsonapi.ext.postgresql_jsonb.filtering.alchemy import create_filters
from flask_rest_jsonapi.ext.postgresql_jsonb.schema import SchemaJSONB
from flask_rest_jsonapi.marshmallow_fields import Relationship
from flask_rest_jsonapi.querystring import QueryStringManager
from sqlalchemy.orm import Query

from flask_rest_jsonapi.plugin import BasePlugin


class PostgreSqlJSONB(BasePlugin):
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
    def _update_qs_filter(cls, qs: QueryStringManager, new_filters):
        """
        Вычищаем фильтры из qs, которые относятся к JSONB
        :param QueryStringManager qs:
        :return:
        """
        new_filters = {
            i_filter['name']: i_filter
            for i_filter in new_filters
        }
        clear_qs = {}
        for k, v in qs.qs.items():
            if k.startswith('filter['):
                f_name = k[7:-1]
                if f_name in new_filters:
                    clear_qs[k] = v
            elif k.startswith('filter'):
                list_filters = json.loads(v)
                new_clear_filter = []
                for i_filter in list_filters:
                    if i_filter.get('name') in new_filters:
                        new_clear_filter.append(i_filter)
                if new_clear_filter:
                    clear_qs[k] = json.dumps(new_clear_filter)
            else:
                clear_qs[k] = v
        qs.qs = ImmutableMultiDict(clear_qs)
        return qs

    @classmethod
    def _filter_query(cls, query, qs: QueryStringManager, model, self_json_api):
        """Filter query according to jsonapi 1.0

        :param Query query: sqlalchemy query to sort
        :param QueryStringManager qs: filter information
        :param DeclarativeMeta model: an sqlalchemy model
        :param self_json_api:
        :return Query: the sorted query
        """
        # Вытащим нужные фильтры по полям JSONB, оставшиеся отправим на разбор самой библиотеки
        filter_for_jsonb = []
        new_filters = []
        for i_filter in qs.filters:
            if i_filter['val'] == '':
                # Пропускаем фильтры с пустой строкой
                continue
            if cls._isinstance_jsonb(self_json_api.resource.schema, i_filter['name']):
                filter_for_jsonb.append(i_filter)
            else:
                new_filters.append(i_filter)
        cls._update_qs_filter(qs, new_filters)

        filters, joins = create_filters(model, filter_for_jsonb, self_json_api.resource)
        for i_join in joins:
            query = query.join(*i_join)
        query = query.filter(*filters)

        return query

    def data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                               view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Во время создания запроса к БД на выгрузку объектов. Тут можно пропатчить запрос к БД
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        if qs.filters:
            query = self._filter_query(query, qs, self_json_api.model, self_json_api=self_json_api)
        return query
