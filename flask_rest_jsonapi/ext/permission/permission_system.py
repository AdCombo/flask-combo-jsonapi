import math
from copy import deepcopy
from typing import Set, List, Dict, Any, Tuple

from sqlalchemy.orm import class_mapper, ColumnProperty

from flask_rest_jsonapi.exceptions import JsonApiException


PERMISSION_TO_MAPPER = Dict[
    str, Dict[
        str, Any
    ]
]


class PermissionToMapper:
    """Содержит все классы пермишеннов в системе сгруппированных по типам get/post/patch/delete"""
    get: PERMISSION_TO_MAPPER = {}
    get_list: PERMISSION_TO_MAPPER = {}
    post: PERMISSION_TO_MAPPER = {}
    patch: PERMISSION_TO_MAPPER = {}
    delete: PERMISSION_TO_MAPPER = {}

    @classmethod
    def add_permission(cls, type_: str, model, permission_class: List) -> None:
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


class PermissionFields:
    """
    В PermissionFields присутствует weight он нужен для задания пермишену веса
    так как есть пермишенны разрешающие, а есть запрещающие, и они могут пересекаться,
    для этого будет нужен вес, пермишен с наибольшим весом победит
    """
    # словарь с разрешёнными столбцами и найбольшим весом пермишена
    # Например: {'id': 4, 'user_id':1}
    _allow_columns = {}
    # словарь с запрещёнными столбцами и найбольшим весом пермишена
    # Например: {'id': 4, 'user_id':1}
    _forbidden_columns = {}
    # Вес данного пермишена. Это нужно для столбцов
    weight = 0

    @classmethod
    def _update_columns(cls, self_columns: Dict[str, int], value: Tuple[List[str], int]) -> None:
        for i_name_col in value[0]:
            old_weight = self_columns.get(i_name_col, -math.inf)
            self_columns[i_name_col] = value[1] if old_weight < value[1] else old_weight

    @property
    def allow_columns(self) -> Dict[str, int]:
        return self._allow_columns

    @allow_columns.setter
    def allow_columns(self, value: Tuple[List[str], int]) -> None:
        self._allow_columns = {}
        self._update_columns(self._allow_columns, value)

    @property
    def forbidden_columns(self) -> Dict[str, int]:
        return self._forbidden_columns

    @forbidden_columns.setter
    def forbidden_columns(self, value: Tuple[List[str], int]) -> None:
        self._forbidden_columns = {}
        self._update_columns(self._forbidden_columns, value)

    def columns_for_jsonb(self, name_col_jsonb):
        """
        Выгружает список доступных полей для схемы JSONB для данного пользователя.
        Если ограничений нет, то вернёт None
        :param name_col_jsonb: название поля, которое является JSONB в БД
        :return:
        """
        columns = deepcopy(self._allow_columns)
        for i_name, i_weight in self._forbidden_columns.items():
            if i_name in columns and columns[i_name] < i_weight:
                del columns[i_name]
        jsonb_columns = {}
        for i_name, i_weight in columns.items():
            if '.' in i_name:
                jsonb_columns[i_name] = i_weight

        # группируем jsonb поля
        jsonb_columns_list_allow = {}
        for i_col in jsonb_columns.keys():
            col_jsonb = i_col.split('.')
            if col_jsonb[0] not in jsonb_columns_list_allow:
                jsonb_columns_list_allow[col_jsonb[0]] = []
            jsonb_columns_list_allow[col_jsonb[0]].append(col_jsonb[1])

        return jsonb_columns_list_allow.get(name_col_jsonb)

    @property
    def columns(self) -> Set[str]:
        """Список столбцов, с которыми пользователь может что-либо делать"""
        columns = deepcopy(self._allow_columns)
        for i_name, i_weight in self._forbidden_columns.items():
            if i_name in columns and columns[i_name] < i_weight:
                del columns[i_name]
        not_jsonb_columns = {}
        for i_name, i_weight in columns.items():
            if '.' not in i_name:
                not_jsonb_columns[i_name] = i_weight
        return set(not_jsonb_columns.keys())

    def __add__(self, other):
        for i_name, i_weight in other._allow_columns.items():
            old_weight = self._allow_columns.get(i_name, -math.inf)
            self._allow_columns[i_name] = i_weight if old_weight < i_weight else old_weight

        for i_name, i_weight in other._forbidden_columns.items():
            old_weight = self._forbidden_columns.get(i_name, -math.inf)
            self._forbidden_columns[i_name] = i_weight if old_weight < i_weight else old_weight
        return self

    def __init__(self, *args, allow_columns: List = None, forbidden_columns: List = None, weight=0, **kwargs):
        allow_columns = allow_columns if allow_columns else []
        forbidden_columns = forbidden_columns if forbidden_columns else []
        self.allow_columns = (allow_columns, weight)
        self.forbidden_columns = (forbidden_columns, weight)
        self.weight = weight


class PermissionForPatch(PermissionFields):
    """Разрешения для пользователя в методе patch"""
    pass


class PermissionForPost(PermissionFields):
    """Разрешения для пользователя в методе post"""
    pass


class PermissionForGet(PermissionFields):
    """Разрешения для пользователя в методе get"""
    # Необходимые фильтры для выгрузки только тех строк, которые доступны данному пользователю (например только
    # активные пользователи)
    filters: List = []
    # joins с другими таблицами для работы фильтров
    joins: List = []

    def __init__(self, allow_columns: List = None, forbidden_columns: List = None,
                 filters: List = None, joins: List = None, weight=0):
        super().__init__(allow_columns=allow_columns, forbidden_columns=forbidden_columns, weight=weight)
        self.filters: List = [] if filters is None else filters
        self.joins: List = [] if joins is None else joins

    def __add__(self, other):
        super().__add__(other)
        self.filters += other.filters
        self.joins += other.joins
        return self


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
        # Уже расчитанные пермишены для POST запроса в данном запросе для current_user
        self._cache_post: Dict[str, PermissionForPost] = dict()
        # Уже расчитанные пермишены для POST запроса в данном запросе для current_user
        self._cache_patch: Dict[str, PermissionForPatch] = dict()

    def _join_permission_get(self, *args, many: bool = True, permission_classes: List = None, **kwargs) -> PermissionForGet:
        # Объеденим все пермишенны, которые доступны данному пользователю
        permission: PermissionForGet = PermissionForGet()
        for i_custom_perm in permission_classes:
            obj_custom_perm = i_custom_perm()
            permission += obj_custom_perm.get(*args, many=many, user_permission=self, **kwargs)
        # Теперь если среди доступных полей есть поля являющиеся ссылками на другие модели, то нужно получить из других
        # моделей доступные поля
        return permission

    def _join_permission_post(self, *args, permission_classes: List = None, **kwargs) -> PermissionForPost:
        # Объеденим все пермишенны, которые доступны данному пользователю для Post запроса
        permission: PermissionForPost = PermissionForPost()
        for i_custom_perm in permission_classes:
            obj_custom_perm = i_custom_perm()
            permission += obj_custom_perm.post_permission(*args, user_permission=self, **kwargs)
        # Теперь если среди доступных полей есть поля являющиеся ссылками на другие модели, то нужно получить из других
        # моделей доступные поля
        return permission

    def _join_permission_patch(self, *args, permission_classes: List = None, **kwargs) -> PermissionForPatch:
        # Объеденим все пермишенны, которые доступны данному пользователю для Patch запроса
        permission: PermissionForPatch = PermissionForPatch()
        for i_custom_perm in permission_classes:
            obj_custom_perm = i_custom_perm()
            permission += obj_custom_perm.patch_permission(*args, user_permission=self, **kwargs)
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
            type_ = 'get_list' if self.many else 'get'
            if model_name in getattr(PermissionToMapper, type_):
                permission_classes = getattr(PermissionToMapper, type_)[model_name]['permission']
                if permission_classes:
                    permission = self._join_permission_get(many=self.many, permission_classes=permission_classes)
                    self._cache_get[model_name] = permission
                    return self._cache_get[model_name]
            # Если у данной схемы нет ограничений знчит доступны все поля в маппере
            self._cache_get[model_name] = PermissionForGet(
                allow_columns=[prop.key for prop in class_mapper(model).iterate_properties if isinstance(prop, ColumnProperty)]
            )
        return self._cache_get[model_name]

    def permission_for_post_permission(self, model) -> PermissionForPost:
        """
        Получить ограничения для определённой модели (маппера) на создание (post)
        :param model: модель
        :return:
        """
        model_name = model.__name__
        if model_name not in self._cache_post:
            if model_name in PermissionToMapper.post:
                permission_classes = PermissionToMapper.post[model_name]['permission']
                if permission_classes:
                    permission = self._join_permission_post(permission_classes=permission_classes)
                    self._cache_post[model_name] = permission
                    return self._cache_post[model_name]
            # Если у данной схемы нет ограничений знчит доступны все поля в маппере
            self._cache_post[model_name] = PermissionForPost(
                allow_columns=[prop.key for prop in class_mapper(model).iterate_properties if isinstance(prop, ColumnProperty)]
            )
        return self._cache_post[model_name]

    def permission_for_patch_permission(self, model) -> PermissionForPatch:
        """
        Получить ограничения для определённой модели (маппера) на изменения (patch)
        :param model: модель
        :return:
        """
        model_name = model.__name__
        if model_name not in self._cache_patch:
            if model_name in PermissionToMapper.patch:
                permission_classes: List = PermissionToMapper.patch[model_name]['permission']
                if permission_classes:
                    permission = self._join_permission_patch(permission_classes=permission_classes)
                    self._cache_patch[model_name] = permission
                    return self._cache_patch[model_name]
            # Если у данной схемы нет ограничений знчит доступны все поля в маппере
            self._cache_patch[model_name] = PermissionForPatch(
                allow_columns=[prop.key for prop in class_mapper(model).iterate_properties if isinstance(prop, ColumnProperty)]
            )
        return self._cache_patch[model_name]

    def permission_for_post_data(self, *args, model, data: Dict, **kwargs) -> Dict:
        """

        :param model: модель
        :param data: данные, которые нужно очистить
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.post:
            permission_classes = PermissionToMapper.post[model_name]['permission']
            for i_custom_perm in permission_classes:
                obj_custom_perm = i_custom_perm()
                data = obj_custom_perm.post_data(*args, data=data, user_permission=self, **kwargs)
        return data

    def permission_for_patch_data(self, *args, model, data: Dict, obj=None, **kwargs) -> Dict:
        """

        :param model: моделиь
        :param data: данные, которые нужно очистить
        :param obj: объект из БД, который обновляем
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.patch:
            permission_classes = PermissionToMapper.patch[model_name]['permission']
            for i_custom_perm in permission_classes:
                obj_custom_perm = i_custom_perm()
                data = obj_custom_perm.patch_data(*args, data=data, obj=obj, user_permission=self, **kwargs)
        return data

    def permission_for_delete(self, *args, model, obj=None, **kwargs) -> None:
        """

        :param model: модель
        :param obj: объект из БД, который удаляем
        :return:
        """
        model_name = model.__name__
        if model_name in PermissionToMapper.patch:
            permission_classes = PermissionToMapper.delete[model_name]['permission']
            for i_custom_perm in permission_classes:
                obj_custom_perm = i_custom_perm()
                if obj_custom_perm.delete(*args, obj=obj, user_permission=self, **kwargs) is False:
                    raise JsonApiException("It is forbidden to delete the object")


class PermissionMixin:
    """Миксин для кейсов с пермишенами"""
    def __init__(self):
        self.permission_for_get: PermissionForGet = PermissionForGet()
        self.permission_for_path: PermissionForPatch = PermissionForPatch()
        self.permission_for_post: PermissionForPost = PermissionForPost()

    def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
        """
        Ограничения на элементы описанные в PermissionForGet для данного пользователя в get запросах
        :param args:
        :param many: запрос отрабатывает для выгрузки списка или одного элемекнта
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return:
        """
        return self.permission_for_get

    def post_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> Dict:
        """
        Предобрат данных в соответствие с ограничениями перед создание объекта
        :param args:
        :param Dict data: входные данные, прошедшие валидацию (через схему в marshmallow)
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return: возвращает очищенные данные в соответствие с пермишенами данного пользователя
        """
        return data

    def post_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPost:
        """
        Ограничения на элементы описанные в PermissionForPost для данного пользователя в post запросах
        :param args:
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return:
        """
        return self.permission_for_post

    def patch_data(self, *args, data=None, obj=None, user_permission: PermissionUser = None, **kwargs) -> Dict:
        """
        Предобрат данных в соответствие с ограничениями перед обновлением объекта
        :param args:
        :param Dict data: входные данные, прошедшие валидацию (через схему в marshmallow)
        :param obj: обновляемый объект из БД
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return: возвращает очищенные данные в соответствие с пермишенами данного пользователя
        """
        return data

    def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
        """
        Ограничения на элементы описанные в PermissionForPatch для данного пользователя в patch запросах
        :param args:
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return:
        """
        return self.permission_for_path

    def delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool:
        """
        Проверка пермишеннов на возможность удалить данный объект (obj). Если хотя бы одна из функций, вернёт False,
        то удаление не произайдёт
        :param args:
        :param obj: удаляемый объект из БД
        :param PermissionUser user_permission: объект, на инстанс с пермишеннами данного пользователя в данном запросе
        :param kwargs:
        :return: True - может удалить, False - нельзя удалить
        """
        return True
