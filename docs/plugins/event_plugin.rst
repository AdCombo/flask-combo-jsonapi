Плагинам EventPlugin
-----------------------

Плагин **EventPlugin** позволяет:

1. Создать событийное API (RPC).
2. Интегрируется с плагином **ApiSpecPlugin** позволяя создавать документацию для RPC и отображать
   вместе с общей документацией. Описание view производится на **yaml**.
3. Интегрируется с плагином **PermissionPlugin**, можно из view получить доступ к ограничения по
   любой моделе. Также доступ к view ограничивается общими декораторами, которые задаются при
   инициализациии API.

Работа с плагином
~~~~~~~~~~~~~~~~~
Чтобы создать RPC API связанного с какой-либо моделью, нужно:

1. Создать класс от :code:`flask_rest_jsonapi.ext.event.resource.EventsResource` ниже будет более
   подробно сказанно об этом
2. В ресурс менеджере появляется атриббут :code:`events` в нём нужно указать класс созданный в
   первом пункте. Если укажите в ресурс менеджере :code:`ResourceDetail`, то в каждую view RPC API
   будет приходить также id модели (которая указана в ресурс менеджере)

Описание работы плагина
"""""""""""""""""""""""

После того как создали класс унаследованный от :code:`flask_rest_jsonapi.ext.event.resource.EventsResource`
любой метод в этом классе начинающиеся с :code:`event_` будет считаться самостоятельной view (вьюшкой).
Адрес новой view будет формироваться в формате :code:`.../<url ресурс менеджера, к которому привязан
данный класс с методами RPC API>/event_<название нашего метода, после event_>`.

**Если описать в созданном классе любой другой метод или аттрибут, то они будут не видны внутри
view.**

Описания view
"""""""""""""

1. Метод :code:`event_<название метода>` должен принимать следующие параметры:
    * :code:`*args`
    * :code:`id: int` - id сущности модели. Если класс с данным view указан в ресурс менеджере
      :code:`ResourceDetail`.
    * :code:`_permission_user: PermissionUser = None` - пермишены для данного авторизованного
      пользователя, при условие что включён плагин **PermissionPlugin**
    * :code:`**kwargs`
2. При описание ответов view используйте формат JSONAPI
3. В начале метода нужно описать документацию к view на yaml, чтобы хорошо прошла интеграция с
   плагином автодокументации **ApiSpecPlugin**

Пример подключения плагина
~~~~~~~~~~~~~~~~~~~~~~~~~~

Рассмторим пример, когда нам нужно загрузить аватарку для пользователя. В примере также подключим
плагин **ApiSpecPlugin**, чтобы посмотреть его в действие

.. code:: python

    import os
    from flask import Flask, request
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import Query, load_only, scoped_session
    from flask_rest_jsonapi.marshmallow_fields import Relationship
    from flask_rest_jsonapi import Api, ResourceList, ResourceDetail
    from flask_rest_jsonapi.plugin import BasePlugin
    from flask_rest_jsonapi.querystring import QueryStringManager
    from flask_rest_jsonapi.ext.event.resource import EventsResource
    from flask_rest_jsonapi.ext.event import EventPlugin
    from flask_rest_jsonapi.ext.spec import ApiSpecPlugin
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)

    """Описание моделей"""

    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        url_avatar = Column(String)
        password = Column(String)


    db.create_all()

    """Описание схем моделей"""

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
        url_avatar = fields.String()
        password = fields.String()

    """Описание ресурс менеджеров для API"""

    class UserEventsForResourceDetail(EventsResource):
        def event_update_avatar(self, *args, id: int = None, **kwargs):
            # language=YAML
            """
            ---
            summary: Обновление аватарки пользователя
            tags:
            - User
            parameters:
            - in: path
              name: id
              required: True
              type: integer
              format: int32
              description: 'id пользователя'
            - in: formData
              name: new_avatar
              type: file
              description: Новая аватарка пользователя
            consumes:
            - application/json
            responses:
              200:
                description: Ничего не вернёт
            """
            user = User.query.filter(User.id == id).one_or_none()
            if user is None:
                raise AccessDenied('You can not work with the user')

            avatar = request.files.get('new_avatar')
            if avatar:
                if avatar:
                    filename = avatar.filename
                    avatar.save(os.path.join(filename))
                user.url_avatar = os.path.join(filename)
                db.session.commit()
            return 'success', 201

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
            EventPlugin()
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