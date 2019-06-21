Работа с плагинами
------------------

Подключение плагинов
~~~~~~~~~~~~~~~~~~~~
Плагины подключаются в момент инициализации APIJSON. Рассмотрим пример подключения плагина **EventPlugin**


.. code:: python

    from flask import Flask
    from flask_rest_jsonapi import Api
    from flask_rest_jsonapi.ext.event import EventPlugin

    app = Flask(__name__)
    api_json = Api(
        app,
        plugins=[
            EventPlugin(),
        ]
    )

API для плагинов
~~~~~~~~~~~~~~~~
**При реализации плагина доступны следующие hooks**

:code:`before_init_plugin(self, *args, app=None, **kwargs) -> None`

    срабатывает перед инициализацией json_api

    - :code:`app` - ссылка на объект приложения Flask

:code:`after_init_plugin(self, *args, app=None, **kwargs) -> None`

    срабатывает после инициализацией json_api

    - :code:`app` - ссылка на объект приложения Flask

:code:`before_route(self, resource: Union[ResourceList, ResourceDetail] = None, view=None, urls: Tuple[str] = None, self_json_api: Api = None, **kwargs) -> None:`

    Предобработка ресурс менеджеров до создания роутера

    - :code:`resource` - ресурс менеджер
    - :code:`view` - название ресурс менеджера
    - :code:`urls` - список url, по которым будет доступен данный ресурс
    - :code:`self_json_api` - ссылка на объект Api

:code:`after_route(self, resource: Union[ResourceList, ResourceDetail] = None, view=None, urls: Tuple[str] = None, self_json_api: Api = None, **kwargs) -> None:`

    Постобработка ресурс менеджеров после создания роутера

    - :code:`resource` - ресурс менеджер
    - :code:`view` - название ресурс менеджера
    - :code:`urls` - список url, по которым будет доступен данный ресурс
    - :code:`self_json_api` - ссылка на объект Api

:code:`after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs) -> None`

    Выполняется после инициализация marshmallow схемы в ResourceList.post

    - :code:`schema` - схема, которая привязана к ресурсу для сериализации/десериализации
    - :code:`model` - модель, которая привязана к ресурсу

:code:`after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs) -> None`

    Выполняется после инициализация marshmallow схемы в ResourceList.get

    - :code:`schema` - схема, которая привязана к ресурсу для сериализации/десериализации
    - :code:`model` - модель, которая привязана к ресурсу

:code:`after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs) -> None`

    Выполняется после инициализация marshmallow схемы в ResourceDetail.get

    - :code:`schema` - схема, которая привязана к ресурсу для сериализации/десериализации
    - :code:`model` - модель, которая привязана к ресурсу

:code:`after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs) -> None`

    Выполняется после инициализация marshmallow схемы в ResourceDetail.patch

    - :code:`schema` - схема, которая привязана к ресурсу для сериализации/десериализации
    - :code:`model` - модель, которая привязана к ресурсу

:code:`data_layer_before_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, **kwargs) -> None`

    Выполняется после десериализации данных и до создания запроса к бд на создание нового объекта

    - :code:`data` - десериализованнаые данные для создания объекта
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`self_json_api` - ссылка на объект Api

:code:`data_layer_create_object_clean_data(self, *args, data: Dict = None, view_kwargs=None, join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict`

    Обрабатывает данные, которые пойдут непосредственно на создание нового объекта. Возвращает обновлённый набор
    данных для нового объекта

    - :code:`Dict data` - данные, на основе которых будет создан новый объект
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`List[str] join_fields` - список полей, которые являются ссылками на другие модели
    - :code:`self_json_api` - ссылка на объект Api

:code:`data_layer_after_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, obj=None, **kwargs) -> None`

    Выполняется после создание нового объекта, но до сохранения в БД

    - :code:`Dict data` - данные, на основе которого был создан новый объект
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`obj` - новый объект, созданный на основе данных data
    - :code:`self_json_api` - ссылка на объект Api

:code:`data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs) -> Query`

    Во время создания запроса к БД на выгрузку объекта. Тут можно пропатчить запрос к БД. Возвращает пропатченный
    запрос к бд

    - :code:`Query query` - сформированный запрос к БД
    - :code:`QueryStringManager qs` - список параметров для запроса
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`self_json_api` - ссылка на объект Api

:code:`data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs) -> Query`

    Во время создания запроса к БД на выгрузку объектов. Тут можно пропатчить запрос к БД. Возвращает пропатченный
    запрос к бд

    - :code:`Query query` - сформированный запрос к БД
    - :code:`QueryStringManager qs` - список параметров для запроса
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`self_json_api` - ссылка на объект Api

:code:`data_layer_update_object_clean_data(self, *args, data: Dict = None, obj=None, view_kwargs=None, join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict`

    Обрабатывает данные, которые пойдут непосредственно на обновления объекта. Возвращает обновлённый набор данных
    для обновления объекта

    - :code:`Dict data` - данные, на основе которых будет создан новый объект
    - :code:`obj` - объект, который будет обновлён
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`self_json_api` - ссылка на объект Api
    - :code:`List[str] join_fields` - список полей, которые являются ссылками на другие модели

:code:`data_layer_delete_object_clean_data(self, *args, obj=None, view_kwargs=None, self_json_api=None, **kwargs) -> None`

    Выполняется до удаления объекта в БД

    - :code:`obj` - удаляемый объект
    - :code:`view_kwargs` - kwargs из ресурс менеджера
    - :code:`self_json_api` - ссылка на объект Api

:code:`before_data_layers_filtering_alchemy_nested_resolve(self, self_nested: Any) -> None`

    Вызывается до создания фильтра в функции Nested.resolve, если после выполнения вернёт None, то дальше
    продолжиться работа функции resolve, если вернёт какое либо значения отличное от None, то функция resolve
    завершается, а результат hook функции передаётся дальше в стеке вызова

    - :code:`self_nested` - instance Nested

:code:`before_data_layers_sorting_alchemy_nested_resolve(self, self_nested: Any) -> None`

    Вызывается до создания сортировки в функции Nested.resolve, если после выполнения вернёт None, то
    дальше продолжиться работа функции resolve, если вернёт какое либо значения отличное от None, То
    функция resolve завершается, а результат hook функции передаётся дальше в стеке вызова

    - :code:`self_nested` - instance Nested

Пример создания плагинов
~~~~~~~~~~~~~~~~~~~~~~~~
Рассмотрим пример реализации плагина, который будет отдавать данные в get запросах для :code:`ResourceList`, :code:`ResourceDetail`
в двух вариантах либо все, либо укороченные по заранее заданному параметру :code:`format=short|full`

.. code:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import Query, load_only, scoped_session
    from flask_rest_jsonapi.marshmallow_fields import Relationship
    from flask_rest_jsonapi import Api, ResourceList, ResourceDetail
    from flask_rest_jsonapi.plugin import BasePlugin
    from flask_rest_jsonapi.querystring import QueryStringManager
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)
    app.config['FLASK_DEBUG'] = 1


    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)


    db.create_all()


    class UserSchema(Schema):
        class Meta:
            type_ = 'user'
            self_view = 'user_detail'
            self_view_kwargs = {'id': '<id>'}
            self_view_many = 'user_list'
            ordered = True

        id = fields.Integer(as_string=True)
        name = fields.String()
        fullname = fields.String()
        email = fields.String()
        password = fields.String()


    class UserResourceList(ResourceList):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name']
        }


    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name']
        }


    class FormatPlugin(BasePlugin):

        def _update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                            view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            all_fields = self_json_api.model.__mapper__.column_attrs.keys()
            short_format = self_json_api.short_format if hasattr(self_json_api, 'short_format') else all_fields
            full_format = self_json_api.full_format if hasattr(self_json_api, 'full_format') else all_fields
            fields = short_format if qs.qs.get('format') == 'short' else full_format

            query = self_json_api.session.query(*[getattr(self_json_api.model, name_field) for name_field in  fields])
            return query

        def data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                                view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            return self._update_query(*args, query=query, qs=qs, view_kwargs=view_kwargs,
                                        self_json_api=self_json_api, **kwargs)

        def data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                                    view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            return self._update_query(*args, query=query, qs=qs, view_kwargs=view_kwargs,
                                        self_json_api=self_json_api, **kwargs)



    api_json = Api(
        app,
        plugins=[
            FormatPlugin(),
        ]
    )
    api_json.route(UserResourceList, 'user_list', '/api/user/')
    api_json.route(UserResourceDetail, 'user_detail', '/api/user/<int:id>/')


    if __name__ == '__main__':
        for i in range(10):
            u = User(name=f'name{i}', fullname=f'fullname{i}', email=f'email{i}', password=f'password{i}')
            db.session.add(u)
        db.session.commit()
        app.run(use_reloader=True)
