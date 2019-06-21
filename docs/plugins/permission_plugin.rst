Плагинам Permission
-----------------------

Плагин **Permission** позволяет:

1. Повесить декораторы на роутеры
2. Добавить ограничительную логику при выгрузке объектов (GET запрос)
    * ограничить выгрузку по атрибутов (они не будут даже загружаться из БД, если только специально к ним не обратятся)
    * ограничить выгрузку по строкам
    * ограничить выгрузку по строкам в зависимости от результатов сложных фильтров, например доступны только те
      пользователи, которые состоят в группе, в которой данный пользователь является владельцем
3. Предобработка данных, которые идут на обновление объекта (PATCH запрос)
4. Предобработка данных, которые идут для создания объекта (POST запрос)
5. Устроить проверку на возможность удаления объекта данным пользователем

Работа с плагином
~~~~~~~~~~~~~~~~~
Чтобы создать систему пермишенов для какой-либо модели, нужно:

1. Создать класс от :code:`flask_rest_jsonapi.ext.permission.permission_system.PermissionMixin` ниже будет более
   подробно сказано об этом
2. В ресурс менеджере в :code:`data_layer` указать какие методы должны использовать данный класс с пермищенами

API класса PermissionMixin
""""""""""""""""""""""""""

**Свойства:**

:code:`permission_for_get: PermissionForGet`

    Разрешения для пользователя в методе get. Содержит свойства

    * :code:`filters: List` - список фильтров, которые нужно применить при выгрузке объектов. Например можем задать, чтобы
      пользовать при выгрузке видел только себя
    * :code:`joins: List` - список джойнов, которые нужно присоединить к данному запросу на выгрузку. Например пользователь
      может увидеть только тех пользователей, которые входят в некую группу, у которая активна
    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`forbidden_columns: Dict[str, int]` - атрибуты модели, которые запрещены и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`columns: Set[str]` - атрибуты модели, доступны пользователю, после сложение разрешающий и запрещающих массивов
      по весу

:code:`permission_for_path: PermissionForPatch`

    Разрешения для пользователя в методе path. Содержит свойства

    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`forbidden_columns: Dict[str, int]` - атрибуты модели, которые запрещены и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`columns: Set[str]` - атрибуты модели, доступны пользователю, после сложение разрешающий и запрещающих массивов
      по весу

:code:`permission_for_post: PermissionForPost`

    Разрешения для пользователя в методе post. Содержит свойства

    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`forbidden_columns: Dict[str, int]` - атрибуты модели, которые запрещены и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`allow_columns: Dict[str, int]` - атрибуты модели, которые доступны и вес доступа, влияет на то что пермишены
      могут быть разрешающими, а могут быть запрещающими
    * :code:`columns: Set[str]` - атрибуты модели, доступны пользователю, после сложение разрешающий и запрещающих массивов
      по весу


**Методы:**

:code:`get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet`

    Ограничения на элементы описанные в PermissionForGet для данного пользователя в get запросах

    - :code:`bool many` - запрашивают через ResourceList или ResourceDetail
    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

:code:`post_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> Dict`

    Предобработка данных в соответствие с ограничениями перед создание объекта. Должен вернуть
    обработанные данные для нового объекта

    - :code:`Dict data` - данные для создания объекта
    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

:code:`post_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPost`

    Ограничения на элементы описанные в PermissionForPost для данного пользователя в post запросах

    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

:code:`patch_data(self, *args, data=None, obj=None, user_permission: PermissionUser = None, **kwargs) -> Dict`

    Предобработка данных в соответствие с ограничениями перед обновлением объекта. Должен вернуть
    обработанные данные для обновления объекта

    - :code:`Dict data` - входные данные, прошедшие валидацию (через схему в marshmallow)
    - :code:`obj` - обновляемый объект из БД
    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

:code:`patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch`

    Ограничения на элементы описанные в PermissionForPatch для данного пользователя в patch запросах

    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

:code:`delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool`

    Проверка пермишеннов на возможность удалить данный объект (obj). Если хотя бы одна из функций,
    вернёт False, то удаление не произойдёт

    - :code:`obj` - обновляемый объект из БД
    - :code:`PermissionUser user_permission` - ограничения для данного пользователя, можно получить доступ к
      ограничениям по другим моделям для данного пользователя для разных методов (get, post, patch)

Описания в ресурс менеджерах
""""""""""""""""""""""""""""

В разделе :code:`data_layer` можно указать следующие типы пермишенов:

* :code:`permission_get: List` - список классов, из которых будет запрашиваться метод :code:`get`
* :code:`permission_post: List` - список классов, из которых будет запрашиваться метод :code:`post_permission` и :code:`post_data`
* :code:`permission_patch: List` - список классов, из которых будет запрашиваться метод :code:`patch_permission` и :code:`patch_data`
* :code:`permission_delete: List` - список классов, из которых будет запрашиваться метод :code:`delete`

Пример подключения плагина
~~~~~~~~~~~~~~~~~~~~~~~~~~

:code:`model`

.. code:: python

    from enum import Enum

    class Role(Enum):
        admin = 1
        limited_user = 2
        user = 3
        block = 4


    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)
        role = Column(Integer)

:code:`permission`

.. code:: python

    from flask_rest_jsonapi.ext.permission.permission_system import PermissionMixin, PermissionForGet, \
        PermissionUser, PermissionForPatch


    class PermissionListUser(PermissionMixin):
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()
        SHORT_INFO_USER = ['id', 'name']

        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
            """Задаём доступные стобцы"""
            if current_user.role == Role.admin.value:
                self.permission_for_get.allow_columns = (self.ALL_FIELDS, 10)
            elif current_user.role in [Role.limited_user.value, Role.user.value]:
                # ограничиваем по атрибутам, а также не дадим видеть заблокированных
                self.permission_for_get.allow_columns = (self.SHORT_INFO_USER, 0)
                self.permission_for_get.filters.append(User.role != Role.block.value)
            return self.permission_for_get

    class PermissionDetailUser(PermissionMixin):
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()
        AVAILABLE_FIELDS_FOR_PATCH = ['password']

        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
            """Задаём доступные стобцы"""
            if current_user.role in [Role.limited_user.value, Role.user.value]:
                # разрешаем смотреть только себя
                self.permission_for_get.filters.append(User.id != current_user.id)
            return self.permission_for_get

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            """Разрешаем менять только пароль"""
            self.permission_for_path.allow_columns = (self.AVAILABLE_FIELDS_FOR_PATCH, 0)
            return self.permission_for_path

        def patch_data(self, *args, data: Dict = None, obj: User = None, user_permission: PermissionUser = None, **kwargs) -> Dict:
            # password
            password = data.get('password')
            if password is not None:
                return {'password': hashlib.md5(password.encode()).hexdigest()}
            return {}

    class PermissionPatchAdminUser(PermissionMixin):
        """Даём админу изменять все поля"""
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            """Разрешаем менять только пароль"""
            if current_user.role == Role.admin.value:
                self.permission_for_path.allow_columns = (self.ALL_FIELDS, 10)  # задаём вес 10, это будет более приоритетно
            return self.permission_for_path

        def patch_data(self, *args, data: Dict = None, obj: User = None, user_permission: PermissionUser = None, **kwargs) -> Dict:
            if current_user.role == Role.admin.value:
                password = data.get('password')
                if password is not None:
                    data['password'] = hashlib.md5(password.encode()).hexdigest()
                return data
            return {}

:code:`views`

.. code:: python

    class UserResourceList(ResourceList):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name'],
            'permission_get': [PermissionListUser],
        }


    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name'],
            'permission_get': [PermissionDetailUser],
            'permission_patch': [PermissionDetailUser, PermissionPatchAdminUser],
        }

:code:`__init__`

.. code:: python

    api_json = Api(
        app,
        decorators=(login_required,),
        plugins=[
            PermissionPlugin(),
        ]
    )