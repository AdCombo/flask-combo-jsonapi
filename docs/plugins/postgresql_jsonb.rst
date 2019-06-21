Плагинам PostgreSqlJSONB
------------------------

Плагин **PostgreSqlJSONB** позволяет:

1. Работать с типом полей **JSONB** в PostgreSql как с обычной моделью в плане выгрузки на клиент
   работает это для **get** запросов в фильтрации и сортировке. Работать можно с полями первого
   уровня.
2. Интегрируется с плагином **ApiSpecPlugin** в swagger в **get** запросах (когда выгружается
   список). Появились доп. поля:

    * :code:`filter[<название JSONB поля в модели>__<название поля верхнего уровня в JSONB>]` - обычные
      фильтры
    * :code:`filter = [{"name": "<название JSONB поля в моделе>__<название поля верхнего уровня
      в JSONB>", "op": "eq", "val": "<значение>"}]` - в составных фильтрах также обращаемся к полям
      внутри JSONB поля, как к полям другой модели.
    * :code:`sort=<название JSONB поля в модели>__<название поля верхнего уровня в JSONB>` - в
      сортировке используется как глубокая сортировка.
3. Интегрируется с плагином **PermissionPlugin**, можно в пермишен кейсах описать ограничения на
   поля верхнего уровня в поле модели JSONB.

Работа с плагином
~~~~~~~~~~~~~~~~~
Чтобы интегрировать плагин в свои схемы, в которых описаны модели с полями JSONB, нужно сделать
следующее:

1. В схеме описываем поле JSONB (из модели) как Nested, на схему со структурой того, что
   планируется хранить в JSONB
2. Схема созданная в первом пункте для хранения структуры из поля модели JSONB должно наследоваться
   от класса :code:`flask_rest_jsonapi.ext.postgresql_jsonb.schema.SchemaJSONB`

И всё :)

Пример подключения плагина
~~~~~~~~~~~~~~~~~~~~~~~~~~

Рассмотрим пример, когда в поле JSONB будем хранить настройки пользователя. Пример будет работать
только с подключение к базе данных postgresql


.. code:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.dialects.postgresql.json import JSONB
    from sqlalchemy.orm import Query, load_only, scoped_session
    from flask_rest_jsonapi.marshmallow_fields import Relationship
    from flask_rest_jsonapi import Api, ResourceList, ResourceDetail
    from flask_rest_jsonapi.querystring import QueryStringManager
    from flask_rest_jsonapi.ext.postgresql_jsonb.schema import SchemaJSONB
    from flask_rest_jsonapi.ext.postgresql_jsonb import PostgreSqlJSONB
    from flask_rest_jsonapi.ext.spec import ApiSpecPlugin
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = '<подключение к Postgresql базе данных>'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)

    """Описание моделей"""

    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)
        settings = Column(JSONB)


    db.create_all()

    """Описание схем моделей"""

    class SettingsSchema(SchemaJSONB):
        active = fields.Boolean()
        age = fields.Integer()

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
        settings = fields.Nested('SettingsSchema')

    """Описание ресурс менеджеров для API"""

    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        events = UserEventsForResourceDetail
        methods = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
        }

    class UserResourceList(ResourceList):
        schema = UserSchema
        methods = ['GET', 'POST']
        data_layer = {
            'session': db.session,
            'model': User,
        }

    """Инициализация API"""

    app.config['OPENAPI_URL_PREFIX'] = '/api/swagger'
    app.config['OPENAPI_SWAGGER_UI_PATH'] = '/'
    app.config['OPENAPI_SWAGGER_UI_VERSION'] = '3.22.0'

    api_spec_plagin = ApiSpecPlugin(
        app=app,
        # Объявляем список тегов и описаний для группировки api в группы (api можно не группировать в группы,
        # в этом случае они будут группирваться автоматически по названию типов схем (type_))
        tags={
            'User': 'API для user'
        }
    )

    api_json = Api(
        app,
        plugins=[
            api_spec_plagin,
            EventPlugin(),
            PostgreSqlJSONB()
        ]
    )
    api_json.route(UserResourceDetail, 'user_detail', '/api/user/<int:id>/', tag='User')
    api_json.route(UserResourceList, 'user_list', '/api/user/', tag='User')


    if __name__ == '__main__':
        for i in range(10):
            u = User(name=f'name{i}', fullname=f'fullname{i}', email=f'email{i}', password=f'password{i}')
            db.session.add(u)
        db.session.commit()
        app.run(port='9999')