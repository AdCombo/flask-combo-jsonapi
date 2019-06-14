from collections import OrderedDict
from functools import wraps
from typing import Union, Tuple, List, Dict

from marshmallow import class_registry, fields
from marshmallow.base import SchemaABC

from flask_rest_jsonapi.exceptions import InvalidInclude

from flask_rest_jsonapi.querystring import QueryStringManager

from flask_rest_jsonapi.schema import get_model_field, get_related_schema
from raven.events import Query
from sqlalchemy.orm import load_only, joinedload

from flask_rest_jsonapi import Api
from flask_rest_jsonapi.ext.permission.permission_system import PermissionUser, PermissionToMapper, PermissionForGet
from flask_rest_jsonapi.resource import ResourceList, ResourceDetail

from flask_rest_jsonapi.plugin import BasePlugin


def permission(method, request_type: str, many=False, decorators=None):

    @wraps(method)
    def wrapper(*args, **kwargs):
        permission_user = PermissionUser(request_type=request_type, many=many)
        return method(*args, **kwargs, _permission_user=permission_user)

    decorators = decorators if decorators else []
    for i_decorator in decorators:
        wrapper = i_decorator(wrapper)
    return wrapper


class PermissionPlugin(BasePlugin):
    def after_route(self,
                    resource: Union[ResourceList, ResourceDetail] = None,
                    view=None,
                    urls: Tuple[str] = None,
                    self_json_api: Api = None,
                    **kwargs) -> None:
        """
        Навешиваем декараторы (с инициализацией пермишенов) на роутеры
        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        model = resource.data_layer['model']

        if issubclass(resource, ResourceList):
            if hasattr(resource, 'get'):
                old_method = getattr(resource, 'get')
                new_method = permission(
                    old_method, request_type='get', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'get', new_method)
                PermissionToMapper.add_permission(type_='get_list', model=model,
                                                  permission_class=resource.data_layer.get('permission_get', []))

            if hasattr(resource, 'post'):
                old_method = getattr(resource, 'post')
                new_method = permission(
                    old_method, request_type='post', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'post', new_method)
                PermissionToMapper.add_permission(type_='post', model=model,
                                                  permission_class=resource.data_layer.get('permission_post', []))

        if issubclass(resource, ResourceDetail):
            if hasattr(resource, 'get'):
                old_method = getattr(resource, 'get')
                new_method = permission(
                    old_method, request_type='get', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'get', new_method)
                PermissionToMapper.add_permission(type_='get', model=model,
                                                  permission_class=resource.data_layer.get('permission_get', []))

            if hasattr(resource, 'patch'):
                old_method = getattr(resource, 'patch')
                new_method = permission(
                    old_method, request_type='patch', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'patch', new_method)
                PermissionToMapper.add_permission(type_='patch', model=model,
                                                  permission_class=resource.data_layer.get('permission_patch', []))

            if hasattr(resource, 'post'):
                old_method = getattr(resource, 'post')
                new_method = permission(
                    old_method, request_type='post', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'post', new_method)
                # Для Post запроса в ResourceDetail не нужны пермишены, они берутся из ResourceList,
                # так как новый элемнт создаётся через ResourceList, а POST запросы в ResourceDetail
                # могут быть связанны с собыйтиным api EventsResource. В собыйтином api безопасность ложится
                # полностью на того кто разрабатывает его, также в любой момент можно обратиться к любому пермишену
                # из любого собыйтиного api, так как ссылка на истанц PermissionUser (активный в контектсе данного
                # api передаётся в kwargs['_permission_user']

            if hasattr(resource, 'delete'):
                old_method = getattr(resource, 'delete')
                new_method = permission(
                    old_method, request_type='delete', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'delete', new_method)
                PermissionToMapper.add_permission(type_='delete', model=model,
                                                  permission_class=resource.data_layer.get('permission_delete', []))

    @classmethod
    def _permission_for_schema(cls, *args, schema=None, model=None, **kwargs):
        """
        Навешиваем ограничения на схему
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        permission_user: PermissionUser = kwargs.get('_permission_user')
        if permission_user is None:
            raise Exception("No permission for user")
        name_fields = set(
            schema._declared_fields.keys()) & \
            permission_user.permission_for_get(model=model).columns
        only = getattr(schema, 'only')
        only = set(only) if only else set(name_fields)
        # Оставляем поля только те, которые пользователь запросил через параметр fields[...]
        only &= set(name_fields)
        only = tuple(only)
        schema.fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})

        setattr(schema, 'only', only)

        # навешиваем ограничения на поля схемы, на которую указывает поле JSONB. Если
        # ограничений нет, то выгружаем все поля
        for i_field_name, i_field in schema.fields.items():
            jsonb_only = permission_user.permission_for_get(model=model).columns_for_jsonb(i_field_name)
            if isinstance(i_field, fields.Nested) and \
                    getattr(getattr(i_field.schema, 'Meta', object), 'filtering', False) and \
                    jsonb_only is not None:
                setattr(i_field.schema, 'only', tuple(jsonb_only))
                i_field.schema.fields = OrderedDict(**{name: val for name, val in i_field.schema.fields.items() if name in jsonb_only})

        include_data = tuple(i_include for i_include in getattr(schema, 'include_data', []) if i_include in name_fields)
        setattr(schema, 'include_data', include_data)
        # Выдераем из схем поля, которые пользователь не должен увидеть
        for i_include in getattr(schema, 'include_data', []):
            if i_include in schema.fields:
                field = get_model_field(schema, i_include)
                i_model = cls._get_model(model, field)
                cls._permission_for_schema(schema=schema._declared_fields[i_include].schema,
                                           model=i_model, **kwargs)

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def data_layer_create_object_clean_data(self, *args, data: Dict = None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs):
        """
        Обрабатывает данные, которые пойдут непосредственно на создание нового объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param self_json_api:
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        return permission.permission_for_post_data(model=self_json_api.model, data=data, join_fields=join_fields, **view_kwargs)

    def data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                           view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Во время создания запроса к БД на выгрузку объекта. Тут можно пропатчить запрос к БД.
        Навешиваем ограничения на запрос, чтобы не тянулись поля из БД, которые данному
        пользователю не доступны. Также навешиваем фильтры, чтобы пользователь не смог увидеть
        записи, которые ему не доступны
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Навешиваем ограничения по атрибутам (которые доступны & которые запросил пользователь)
        name_columns = permission_for_get.columns
        user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
        if user_requested_columns:
            name_columns = list(set(name_columns) & set(user_requested_columns))
        query = query.options(load_only(*name_columns))
        query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)

        # Запретим использовать стандартную функцию eagerload_includes для присоединения сторонних молелей
        self_json_api.eagerload_includes = lambda x, y: x
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
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Навешиваем ограничения по атрибутам (которые доступны & которые запросил пользователь)
        name_columns = permission_for_get.columns
        user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
        if user_requested_columns:
            name_columns = list(set(name_columns) & set(user_requested_columns))
        query = query.options(load_only(*name_columns))

        # Запретим использовать стандартную функцию eagerload_includes для присоединения сторонних молелей
        setattr(self_json_api, 'eagerload_includes', False)
        query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)
        return query

    def data_layer_update_object_clean_data(self, *args, data: Dict = None, obj=None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict:
        """
        Обрабатывает данные, которые пойдут непосредственно на обновления объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param obj: Объект, который будет обновлён
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param self_json_api:
        :param kwargs:
        :return: возвращает обновлённый набор данных для нового объекта
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        clean_data = permission.permission_for_patch_data(model=self_json_api.model, data=data, obj=obj,
                                                          join_fields=join_fields, **view_kwargs)
        return clean_data

    def data_layer_delete_object_clean_data(self, *args, obj=None, view_kwargs=None, self_json_api=None, **kwargs) -> None:
        """
        Выполняется до удаления объекта в БД
        :param args:
        :param obj: удаляемый объект
        :param view_kwargs:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission.permission_for_delete(model=self_json_api.model, obj=obj, **view_kwargs)

    @classmethod
    def _get_permission_user(cls, view_kwargs) -> PermissionUser:
        permission_user = view_kwargs.get('_permission_user')
        if permission_user is not None:
            return permission_user
        raise Exception("No permission for user")

    @classmethod
    def _get_model(cls, model, name_foreign_key: str) -> str:
        """
        Возвращает модель, на которую указывает "внешний ключ"
        :param model: модель, из которой взят "внешний ключ" name_foreign_key
        :param str name_foreign_key: "внешний ключ", например "manager_id" или "manager_id.group_id"
        :return:
        """
        mapper = model
        for i_name_foreign_key in name_foreign_key.split('.'):
            mapper_old = mapper
            mapper = getattr(mapper_old, i_name_foreign_key, None)
            if mapper is None:
                # Внешний ключ должен присутствовать в маппере
                raise ValueError('Not foreign ket %s in mapper %s' % (i_name_foreign_key, mapper_old.__name__))
            mapper = mapper.mapper.class_
        return mapper

    @classmethod
    def _is_access_foreign_key(cls, name_foreign_key: str, model, permission: PermissionUser = None) -> bool:
        """
        Проверяет есть ли доступ к данному внешнему ключу
        :param name_foreign_key: название внешнего ключа, например "manager_id" или "manager_id.group_id"
        :param model: маппер, с которого начинается проверка внешнего ключа name_foreign_key
        :return:
        """
        permission_for_get: PermissionForGet = permission.permission_for_get(model)
        name_foreign_key = name_foreign_key.split('.')[-1]
        if name_foreign_key not in permission_for_get.columns:
            return False
        return True

    @classmethod
    def _get_access_fields_in_schema(cls, name_foreign_key: str, cls_schema, permission: PermissionUser = None,
                                     model=None) -> List[str]:
        """
        Получаем список названий полей, которые доступны пользователю и есть в схеме
        :param name_foreign_key: название "внешнего ключа"
        :param cls_schema: класс со схемой
        :param PermissionUser permission: пермишены для пользователя
        :param model:
        :return:
        """
        # Вытаскиваем модель на которую ссылается "внешний ключ", чтобы получить ограничения на неё
        # для данного пользователя
        field_foreign_key = get_model_field(cls_schema, name_foreign_key)
        mapper = cls._get_model(model, field_foreign_key)
        permission_for_get: PermissionForGet = permission.permission_for_get(mapper)
        # ограничиваем выгрузку полей в соответствие с пермишенами
        if permission_for_get.columns is not None:
            name_columns = list(set(cls_schema._declared_fields.keys()) & permission_for_get.columns)
            return name_columns
        return []

    @classmethod
    def _eagerload_includes(cls, query, qs, permission: PermissionUser = None, self_json_api=None):
        """Переопределил и доработал функцию eagerload_includes в SqlalchemyDataLayer, с целью навешать ограничение (для данного
        пермишена) на выдачу полей из БД для модели, на которую ссылается relationship
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter

        :param Query query: sqlalchemy queryset
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param PermissionUser permission: пермишены для пользователя
        :param self_json_api:
        :return Query: the query with includes eagerloaded
        """
        for include in qs.include:
            joinload_object = None

            if '.' in include:
                current_schema = self_json_api.resource.schema
                model = self_json_api.model
                for obj in include.split('.'):
                    try:
                        field = get_model_field(current_schema, obj)
                    except Exception as e:
                        raise InvalidInclude(str(e))

                    # Возможно пользовать неимеет доступа, к данному внешнему ключу
                    if cls._is_access_foreign_key(obj, model, permission) is False:
                        continue
                    try:
                        # Нужный внешний ключ может отсутствовать
                        model = cls._get_model(model, field)
                    except ValueError as e:
                        raise InvalidInclude(str(e))

                    if joinload_object is None:
                        joinload_object = joinedload(field)
                    else:
                        joinload_object = joinload_object.joinedload(field)

                    # ограничиваем список полей (которые доступны & которые запросил пользователь)
                    name_columns = cls._get_access_fields_in_schema(obj, current_schema, model=model)
                    user_requested_columns = qs.fields.get(current_schema.Meta.type_)
                    if user_requested_columns:
                        name_columns = set(name_columns) & set(user_requested_columns)
                    joinload_object.load_only(*list(name_columns))

                    related_schema_cls = get_related_schema(current_schema, obj)

                    if isinstance(related_schema_cls, SchemaABC):
                        related_schema_cls = related_schema_cls.__class__
                    else:
                        related_schema_cls = class_registry.get_class(related_schema_cls)

                    current_schema = related_schema_cls
            else:
                try:
                    field = get_model_field(self_json_api.resource.schema, include)
                except Exception as e:
                    raise InvalidInclude(str(e))

                # Возможно пользовать неимеет доступа, к данному внешнему ключу
                if cls._is_access_foreign_key(include, self_json_api.model, permission) is False:
                    continue

                joinload_object = joinedload(getattr(self_json_api.model, field))

                # ограничиваем список полей (которые доступны & которые запросил пользователь)
                name_columns = cls._get_access_fields_in_schema(include, self_json_api.resource.schema, permission,
                                                                model=self_json_api.model)
                user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
                if user_requested_columns:
                    name_columns = set(name_columns) & set(user_requested_columns)
                joinload_object.load_only(*list(name_columns))

            query = query.options(joinload_object)

        return query
