"""Base class for Plugin classes."""
from typing import Union, List, Tuple

from flask_rest_jsonapi import Api
from flask_rest_jsonapi.exceptions import PluginMethodNotImplementedError
from flask_rest_jsonapi.resource import ResourceDetail, ResourceList


class BasePlugin(object):
    """Base class for JsonAPI plugin classes."""
    def before_init_plugin(self, *args, app=None, **kwargs):
        """Перед инициализацией json_api"""
        raise PluginMethodNotImplementedError

    def after_init_plugin(self, *args, app=None, **kwargs):
        """После инициализацией json_api"""
        raise PluginMethodNotImplementedError

    def before_route(self,
                     resource: Union[ResourceList, ResourceDetail] = None,
                     view=None,
                     urls: Tuple[str] = None,
                     self_json_api: Api = None,
                     **kwargs) -> None:
        """
        Предобработка ресурс менеджеров до создания роутера
        :param resource: ресурс менеджер
        :param view: название ресурс менеджера
        :param urls: список url, по которым будет доступен данный ресурс
        :param self_json_api: self json_api
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_route(self,
                    resource: Union[ResourceList, ResourceDetail] = None,
                    view=None,
                    urls: Tuple[str] = None,
                    self_json_api: Api = None,
                    **kwargs) -> None:
        """
        Постбработка ресурс менеджеров после создания роутера
        :param resource: ресурс менеджер
        :param view: название ресурс менеджера
        :param urls: список url, по которым будет доступен данный ресурс
        :param self_json_api: self json_api
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs):
        """
        Выполняется после иницциализация marshmallow схемы в ResourceList.post
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs):
        """
        Выполняется после иницциализация marshmallow схемы в ResourceList.get
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs):
        """
        Выполняется после иницциализация marshmallow схемы в ResourceDetail.get
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs):
        """
        Выполняется после иницциализация marshmallow схемы в ResourceDetail.patch
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError
