from collections import OrderedDict
from functools import wraps
from typing import Union, Tuple

from flask_rest_jsonapi import Api
from flask_rest_jsonapi.ext.permission.permission_system import PermissionUser
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
        if issubclass(resource, ResourceList):
            if hasattr(resource, 'get'):
                old_method = getattr(resource, 'get')
                new_method = permission(
                    old_method, request_type='get', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'get', new_method)
            if hasattr(resource, 'post'):
                old_method = getattr(resource, 'post')
                new_method = permission(
                    old_method, request_type='post', many=False, decorators=self_json_api.decorators)
                setattr(resource, 'post', new_method)

        if issubclass(resource, ResourceDetail):
            if hasattr(resource, 'get'):
                old_method = getattr(resource, 'get')
                new_method = permission(
                    old_method, request_type='get', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'get', new_method)
            if hasattr(resource, 'patch'):
                old_method = getattr(resource, 'patch')
                new_method = permission(
                    old_method, request_type='patch', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'patch', new_method)
            if hasattr(resource, 'post'):
                old_method = getattr(resource, 'post')
                new_method = permission(
                    old_method, request_type='post', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'post', new_method)
            if hasattr(resource, 'delete'):
                old_method = getattr(resource, 'delete')
                new_method = permission(
                    old_method, request_type='delete', many=True, decorators=self_json_api.decorators)
                setattr(resource, 'delete', new_method)

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
        only = only if only else []
        only += list(name_fields)
        schema.fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})

        setattr(schema, 'only', only)

        include_data = tuple(i_include for i_include in getattr(schema, 'include_data', []) if i_include in name_fields)
        setattr(schema, 'include_data', include_data)

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)
