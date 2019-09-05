"""Base class for Plugin classes."""
from typing import List, Tuple, Dict, Any

from sqlalchemy.orm import Query

from flask_rest_jsonapi.exceptions import PluginMethodNotImplementedError


class BasePlugin(object):
    """Base class for JsonAPI plugin classes."""
    def before_init_plugin(self, *args, app=None, **kwargs) -> None:
        """Перед инициализацией json_api"""
        raise PluginMethodNotImplementedError

    def after_init_plugin(self, *args, app=None, **kwargs) -> None:
        """После инициализацией json_api"""
        raise PluginMethodNotImplementedError

    def before_route(self,
                     resource: Any = None,
                     view=None,
                     urls: Tuple[str] = None,
                     self_json_api: Any = None,
                     **kwargs) -> None:
        """
        Предобработка ресурс менеджеров до создания роутера
        :param Union[ResourceList, ResourceDetail] resource: ресурс менеджер
        :param view: название ресурс менеджера
        :param urls: список url, по которым будет доступен данный ресурс
        :param Api self_json_api: self json_api
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_route(self,
                    resource: Any = None,
                    view=None,
                    urls: Tuple[str] = None,
                    self_json_api: Any = None,
                    **kwargs) -> None:
        """
        Постбработка ресурс менеджеров после создания роутера
        :param Union[ResourceList, ResourceDetail] resource: ресурс менеджер
        :param view: название ресурс менеджера
        :param urls: список url, по которым будет доступен данный ресурс
        :param Api self_json_api: self json_api
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs) -> None:
        """
        Выполняется после иницциализация marshmallow схемы в ResourceList.post
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs) -> None:
        """
        Выполняется после иницциализация marshmallow схемы в ResourceList.get
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs) -> None:
        """
        Выполняется после иницциализация marshmallow схемы в ResourceDetail.get
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs) -> None:
        """
        Выполняется после иницциализация marshmallow схемы в ResourceDetail.patch
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def data_layer_before_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, **kwargs) -> None:
        """
        Выполняется после десериализации данных и до создания запроса к бд на создание нового объекта
        :param args:
        :param data:
        :param view_kwargs:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def data_layer_create_object_clean_data(self, *args, data: Dict = None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict:
        """
        Обрабатывает данные, которые пойдут непосредственно на создание нового объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param Api self_json_api:
        :param kwargs:
        :return: возвращает обновлённый набор данных для нового объекта
        """
        raise PluginMethodNotImplementedError

    def data_layer_after_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, obj=None,
                                       **kwargs) -> None:
        """
        Выполняется после создание нового объекта, но до сохранения в БД
        :param args:
        :param data:
        :param view_kwargs:
        :param Api self_json_api:
        :param obj:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def data_layer_get_object_update_query(self, *args, query: Query = None, qs: Any = None,
                                           view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Во время создания запроса к БД на выгрузку объекта. Тут можно пропатчить запрос к БД
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param Api self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        raise PluginMethodNotImplementedError

    def data_layer_get_collection_update_query(self, *args, query: Query = None, qs: Any = None,
                                               view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Во время создания запроса к БД на выгрузку объектов. Тут можно пропатчить запрос к БД
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param Api self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        raise PluginMethodNotImplementedError

    def data_layer_update_object_clean_data(self, *args, data: Dict = None, obj=None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict:
        """
        Обрабатывает данные, которые пойдут непосредственно на обновления объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param obj: Объект, который будет обновлён
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param Api self_json_api:
        :param kwargs:
        :return: возвращает обновлённый набор данных для обновления объекта
        """
        raise PluginMethodNotImplementedError

    def data_layer_delete_object_clean_data(self, *args, obj=None, view_kwargs=None, self_json_api=None,
                                            **kwargs) -> None:
        """
        Выполняется до удаления объекта в БД
        :param args:
        :param obj: удаляемый объект
        :param view_kwargs:
        :param Api self_json_api:
        :param kwargs:
        :return:
        """
        raise PluginMethodNotImplementedError

    def before_data_layers_filtering_alchemy_nested_resolve(self, self_nested: Any) -> Any:
        """
        Вызывается до создания фильтра в функции Nested.resolve, если после выполнения вернёт None, то
        дальше продолжиться работа функции resolve, если вернёт какое либо значения отличное от None, То
        функция resolve завершается, а результат hook функции передаётся дальше в стеке вызова
        :param Nested self_nested: instance Nested
        :return:
        """
        raise PluginMethodNotImplementedError

    def before_data_layers_sorting_alchemy_nested_resolve(self, self_nested: Any) -> Any:
        """
        Вызывается до создания сортировки в функции Nested.resolve, если после выполнения вернёт None, то
        дальше продолжиться работа функции resolve, если вернёт какое либо значения отличное от None, То
        функция resolve завершается, а результат hook функции передаётся дальше в стеке вызова
        :param Nested self_nested: instance Nested
        :return:
        """
        raise PluginMethodNotImplementedError
