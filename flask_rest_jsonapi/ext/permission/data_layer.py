from functools import reduce

from sqlalchemy import inspect
from sqlalchemy.orm.exc import NoResultFound
from typing import List

from flask_rest_jsonapi import JsonApiException
from flask_rest_jsonapi.exceptions import InvalidInclude, ObjectNotFound
from flask_rest_jsonapi.ext.permission.permission_system import PermissionForGet, PermissionUser
from flask_rest_jsonapi.schema import get_model_field, get_related_schema, get_relationships, get_nested_fields
from marshmallow import class_registry
from marshmallow.base import SchemaABC
from flask_rest_jsonapi.data_layers.alchemy import SqlalchemyDataLayer
from sqlalchemy.orm import load_only, joinedload
from werkzeug.exceptions import Locked


class PGPermissionDataLayer(SqlalchemyDataLayer):

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
            mapper = getattr(mapper, i_name_foreign_key, None)
            if mapper is None:
                # Внешний ключ должен присутствовать в маппере
                raise ValueError('Not foreign ket %s in mapper %s' % (i_name_foreign_key, mapper.__name__))
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
    def _get_access_fields_in_schema(cls, name_foreign_key: str, cls_schema, permission: PermissionUser = None, model=None) -> List[str]:
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

    def eagerload_includes(self, query, qs, permission: PermissionUser = None):
        """Переопределил и доработал функцию eagerload_includes в SqlalchemyDataLayer, с целью навешать ограничение (для данного
        пермишена) на выдачу полей из БД для модели, на которую ссылается relationship
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter

        :param Query query: sqlalchemy queryset
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param PermissionUser permission: пермишены для пользователя
        :return Query: the query with includes eagerloaded
        """
        for include in qs.include:
            joinload_object = None

            if '.' in include:
                current_schema = self.resource.schema
                model = self.model
                for obj in include.split('.'):
                    try:
                        field = get_model_field(current_schema, obj)
                    except Exception as e:
                        raise InvalidInclude(str(e))

                    # Возможно пользовать неимеет доступа, к данному внешнему ключу
                    if self._is_access_foreign_key(obj, model, permission) is False:
                        continue
                    try:
                        # Нужный внешний ключ может отсутствовать
                        model = self._get_model(model, field)
                    except ValueError as e:
                        raise InvalidInclude(str(e))

                    if joinload_object is None:
                        joinload_object = joinedload(field)
                    else:
                        joinload_object = joinload_object.joinedload(field)

                    # ограничиваем список полей
                    name_columns = self._get_access_fields_in_schema(obj, current_schema, model=model)
                    joinload_object.load_only(*list(name_columns))

                    related_schema_cls = get_related_schema(current_schema, obj)

                    if isinstance(related_schema_cls, SchemaABC):
                        related_schema_cls = related_schema_cls.__class__
                    else:
                        related_schema_cls = class_registry.get_class(related_schema_cls)

                    current_schema = related_schema_cls
            else:
                try:
                    field = get_model_field(self.resource.schema, include)
                except Exception as e:
                    raise InvalidInclude(str(e))

                # Возможно пользовать неимеет доступа, к данному внешнему ключу
                if self._is_access_foreign_key(include, self.model, permission) is False:
                    continue

                joinload_object = joinedload(getattr(self.model, field))
                # ограничиваем список полей
                name_columns = self._get_access_fields_in_schema(include, self.resource.schema, permission, model=self.model)
                joinload_object.load_only(*list(name_columns))

            query = query.options(joinload_object)

        return query

    def get_collection(self, qs, view_kwargs):
        """Retrieve a collection of objects through sqlalchemy

        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param dict view_kwargs: kwargs from the resource view
        :return tuple: the number of object and the list of objects
        """
        # Нужно выталкивать из sqlalchemy Закешированные запросы, иначе не удастся загрузить данные о current_user
        self.session.expire_all()
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self.model)

        self.before_get_collection(qs, view_kwargs)

        query = self.query(view_kwargs)
        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        if qs.filters:
            query = self.filter_query(query, qs.filters, self.model)

        if qs.sorting:
            query = self.sort_query(query, qs.sorting)

        object_count = query.count()

        if getattr(self, 'eagerload_includes', True):
            query = self.eagerload_includes(query, qs, permission)
        # Навешиваем ограничения по атрибутам
        query = query.options(load_only(*permission_for_get.columns))

        query = self.paginate_query(query, qs.pagination)

        collection = query.all()

        collection = self.after_get_collection(collection, qs, view_kwargs)

        return object_count, collection

    def create_object(self, data, view_kwargs):
        """Create an object through sqlalchemy

        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object from sqlalchemy
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)

        self.before_create_object(data, view_kwargs)

        relationship_fields = get_relationships(self.resource.schema, model_field=True)
        nested_fields = get_nested_fields(self.resource.schema, model_field=True)

        join_fields = relationship_fields + nested_fields

        clean_data = permission.permission_for_post(model=self.model, data=data)
        obj = self.model(**{key: value
                            for (key, value) in clean_data.items() if key not in join_fields})
        self.apply_relationships(data, obj)
        self.apply_nested_fields(data, obj)

        self.session.add(obj)
        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Object creation error: " + str(e), source={'pointer': '/data'})

        self.after_create_object(obj, data, view_kwargs)

        return obj

    def get_object(self, view_kwargs, qs=None):
        """Retrieve an object through sqlalchemy

        :params dict view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object from sqlalchemy
        """
        # Нужно выталкивать из sqlalchemy Закешированные запросы, иначе не удастся загрузить данные о current_user
        self.session.expire_all()
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self.model)

        self.before_get_object(view_kwargs)

        id_field = getattr(self, 'id_field', inspect(self.model).primary_key[0].key)
        try:
            filter_field = getattr(self.model, id_field)
        except Exception:
            raise Exception("{} has no attribute {}".format(self.model.__name__, id_field))

        url_field = getattr(self, 'url_field', 'id')
        filter_value = view_kwargs[url_field]

        query = self.retrieve_object_query(view_kwargs, filter_field, filter_value)
        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        if qs is not None:
            query = self.eagerload_includes(query, qs, permission)
        # Навешиваем ограничения по атрибутам
        query = query.options(load_only(*permission_for_get.columns))

        try:
            obj = query.one()
        except NoResultFound:
            obj = None

        self.after_get_object(obj, view_kwargs)

        return obj

    def update_object(self, obj, data, view_kwargs):
        """Update an object through sqlalchemy

        :param DeclarativeMeta obj: an object from sqlalchemy
        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if object have changed else False
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)

        if obj is None:
            url_field = getattr(self, 'url_field', 'id')
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound('{}: {} not found'.format(self.model.__name__, filter_value),
                                 source={'parameter': url_field})

        self.before_update_object(obj, data, view_kwargs)

        relationship_fields = get_relationships(self.resource.schema, model_field=True)
        nested_fields = get_nested_fields(self.resource.schema, model_field=True)

        join_fields = relationship_fields + nested_fields

        clean_data = permission.permission_for_patch(model=self.model, data=data)
        for key, value in clean_data.items():
            if hasattr(obj, key) and key not in join_fields:
                setattr(obj, key, value)

        self.apply_relationships(data, obj)
        # self.apply_nested_fields(data, obj)

        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            orig_e = getattr(e, 'orig', object)
            message = getattr(orig_e, 'args', [])
            message = message[0] if message else None
            e = message if message else e
            raise JsonApiException("Update object error: " + str(e), source={'pointer': '/data'})

        self.after_update_object(obj, data, view_kwargs)

    def delete_object(self, obj, view_kwargs):
        """Delete an object through sqlalchemy

        :param DeclarativeMeta item: an item from sqlalchemy
        :param dict view_kwargs: kwargs from the resource view
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)

        if obj is None:
            url_field = getattr(self, 'url_field', 'id')
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound('{}: {} not found'.format(self.model.__name__, filter_value),
                                 source={'parameter': url_field})

        self.before_delete_object(obj, view_kwargs)

        permission.permission_for_patch(model=self.model)

        self.session.delete(obj)
        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Delete object error: " + str(e))

        self.after_delete_object(obj, view_kwargs)
