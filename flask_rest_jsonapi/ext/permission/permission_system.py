from typing import Set, List, Dict

from sqlalchemy import Column
from sqlalchemy.orm import class_mapper, ColumnProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute

from flask_rest_jsonapi.exceptions import JsonApiException


class PermissionToMapper:
    """Содержит все классы пермишеннов в системе сгруппированных по типам get/post/patch/delete"""
    get = {}
    post = {}
    patch = {}
    delete = {}

    @classmethod
    def add_permission(cls, type_: str, model, permission_class) -> None:
        """
        Добавляет новый класс с пермишенными
        :param type_: get | post | patch | delete
        :param model: маппер sqlalchemy для чьих полей описаны пермишены
        :param permission_class: класс с пермишенными
        :return:
        """
        data = getattr(cls, type_)
        data[model.__name__] = {
            'model': model,
            'permission': permission_class
        }


class MetaPermission(type):
    def __new__(mcs, classname, bases, dct):
        """
        Создаём общий объект с пермишенами для моделей
        :param classname:
        :param bases:
        :param dct:
        :return:
        """
        new_mapper = super(MetaPermission, mcs).__new__(mcs, classname, bases, dct)
        PermissionToMapper.add_permission(dct['Meta'].type_, dct['Meta'].model, new_mapper)
        return new_mapper


class PermissionForPatch:
    # Список столбцов, к которые может изменить пользователь
    columns: Set = set()

    def __init__(self, columns: Set = None):
        self.columns: Set = set() if columns is None else columns

    def __add__(self, other):
        self.columns |= set(other.columns)


class PermissionForGet:
    # Список столбцов, к которым пользователь имеет доступ
    columns: Set = set()
    # Необходимые фильтры для выгрузки только тех строк, которые доступны данному пользователю (например только
    # активные пользователи)
    filters: List = []
    # joins с другими таблицами для работы фильтров
    joins: List = []

    def __init__(self, columns: Set = None, filters: List = None, joins: List = None):
        self.columns: Set = set() if columns is None else columns
        self.filters: List = [] if filters is None else filters
        self.joins: List = [] if joins is None else joins

    def __add__(self, other):
        self.columns |= set(other.columns)
        self.filters += other.filters
        self.joins += other.joins
        return self


class PermissionRelationship:
    # список имён внешних ключей, которые ссылаются на одну и ту же модель
    list_columns_name: List[str] = []
    # ограничения у данного пользователя для данного маппера
    permission: PermissionForGet = PermissionForGet

    def __init__(self, column_name: str, permission: PermissionForGet):
        self.list_columns_name = [column_name]
        self.permission = permission


class PermissionUser:
    """Ограничения для данного пользователя"""
    def __init__(self, request_type: str, many: bool = False):
        """
        :param request_type: тип запроса get|post|delete|patch
        :param many: один элемент или множество
        """
        self.request_type: str = request_type
        self.many: bool = many
        # Уже расчитанные пермишены для GET запроса в данном запросе для current_user
        self._cache_get: Dict[str, PermissionForGet] = dict()

    @classmethod
    def _join_permission_get(cls, many, permission_class) -> PermissionForGet:
        # Объеденим все пермишенны, которые доступны данному пользователю
        permission: PermissionForGet = PermissionForGet()
        for i_custom_perm in getattr(permission_class.Meta, 'permission', []):
            obj_custom_perm = i_custom_perm()
            permission += obj_custom_perm.get(many=many)
        # Теперь если среди доступных полей есть поля являющиеся ссылками на другие модели, то нужно получить из других
        # моделей доступные поля
        return permission

    def permission_for_get(self, model) -> PermissionForGet:
        """
        Получить ограничения для определённой модели (маппера) на выгрузку (get)
        :param model: модель
        :return:
        """
        model_name = model.__name__
        if model_name not in self._cache_get:
            if model_name in PermissionToMapper.get:
                permission_class = PermissionToMapper.get[model_name]['permission']
                permission = self._join_permission_get(self.many, permission_class)
                self._cache_get[model_name] = permission
            else:
                # Если у данной схемы нет ограничений знчит доступны все поля в маппере
                self._cache_get[model_name] = PermissionForGet(
                    columns=set([prop.key for prop in class_mapper(model).iterate_properties if isinstance(prop, ColumnProperty)])
                )
        return self._cache_get[model_name]

    def permission_for_post(self, model, data: Dict) -> Dict:
        """

        :param model: модель
        :param data: данные, которые нужно очистить
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.post:
            permission_class = PermissionToMapper.post[model_name]['permission']
            for i_custom_perm in getattr(permission_class.Meta, 'permission', []):
                obj_custom_perm = i_custom_perm()
                data = obj_custom_perm.post(data=data)
        return data

    def permission_for_patch(self, model, data: Dict) -> Dict:
        """

        :param model: моделиь
        :param data: данные, которые нужно очистить
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.patch:
            permission_class = PermissionToMapper.patch[model_name]['permission']
            for i_custom_perm in getattr(permission_class.Meta, 'permission', []):
                obj_custom_perm = i_custom_perm()
                data = obj_custom_perm.patch(data=data)
        return data

    def permission_for_delete(self, model) -> None:
        """

        :param model: модель
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.patch:
            permission_class = PermissionToMapper.delete[model_name]['permission']
            for i_custom_perm in getattr(permission_class.Meta, 'permission', []):
                if i_custom_perm() is False:
                    raise JsonApiException("It is forbidden to delete the object")


class PermissionMixin:
    """Миксин для кейсов с пермишенами"""
    def __init__(self):
        self.permission_for_get: PermissionForGet = PermissionForGet()
        self.permission_for_path: PermissionForPatch = PermissionForPatch()

    def get(self, *args, many=True) -> PermissionForGet:
        return self.permission_for_get

    def post(self, *args, data=None):
        return data

    def patch(self, *args, data=None):
        return data

    def delete(self, *args):
        pass
