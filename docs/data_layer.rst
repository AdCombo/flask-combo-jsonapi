.. _data_layer:

Data layer
==========

.. currentmodule:: flask_combo_jsonapi

| The data layer is a CRUD interface between resource manager and data. It is a very flexible system to use any ORM or data storage. You can even create a data layer that uses multiple ORMs and data storage to manage your own objects. The data layer implements a CRUD interface for objects and relationships. It also manages pagination, filtering and sorting.
|
| Flask-COMBO-JSONAPI has a full-featured data layer that uses the popular ORM `SQLAlchemy <https://www.sqlalchemy.org/>`_.

.. note::

    The default data layer used by a resource manager is the SQLAlchemy one. So if that's what you want to use, you don't have to specify the class of the data layer in the resource manager

To configure the data layer you have to set its required parameters in the resource manager.

Example:

.. code-block:: python

    from flask_combo_jsonapi import ResourceList
    from your_project.schemas import PersonSchema
    from your_project.models import Person

    class PersonList(ResourceList):
        schema = PersonSchema
        data_layer = {'session': db.session,
                      'model': Person}

You can also plug additional methods into your data layer in the resource manager. There are two kinds of additional methods:

* query: the "query" additional method takes view_kwargs as parameter and returns an alternative query to retrieve the collection of objects in the GET method of the ResourceList manager.

* pre-/postprocess methods: all CRUD and relationship(s) operations have pre-/postprocess methods.
Thanks to these you can do additional work before and after each operation of the data layer.
Parameters of each pre-/postprocess method are available in the `flask_combo_jsonapi.data_layers.base.Base <https://github.com/AdCombo/flask-combo-jsonapi/blob/master/flask_combo_jsonapi/data_layers/base.py>`_ base class.

Example:

.. code-block:: python

    from sqlalchemy.orm.exc import NoResultFound
    from flask_combo_jsonapi import ResourceList
    from flask_combo_jsonapi.exceptions import ObjectNotFound
    from your_project.models import Computer, Person

    class ComputerList(ResourceList):
        def query(self, view_kwargs):
            query_ = self.session.query(Computer)
            if view_kwargs.get('id') is not None:
                try:
                    self.session.query(Person).filter_by(id=view_kwargs['id']).one()
                except NoResultFound:
                    raise ObjectNotFound({'parameter': 'id'}, "Person: {} not found".format(view_kwargs['id']))
                else:
                    query_ = query_.join(Person).filter(Person.id == view_kwargs['id'])
            return query_

        def before_create_object(self, data, view_kwargs):
            if view_kwargs.get('id') is not None:
                person = self.session.query(Person).filter_by(id=view_kwargs['id']).one()
                data['person_id'] = person.id

        schema = ComputerSchema
        data_layer = {'session': db.session,
                      'model': Computer,
                      'methods': {'query': query,
                                  'before_create_object': before_create_object}}

.. note::

    You don't have to declare additional data layer methods in the resource manager. You can declare them in a dedicated module or in the model's declaration.

Example:

.. code-block:: python

    from sqlalchemy.orm.exc import NoResultFound
    from flask_combo_jsonapi import ResourceList
    from flask_combo_jsonapi.exceptions import ObjectNotFound
    from your_project.models import Computer, Person
    from your_project.additional_methods.computer import before_create_object

    class ComputerList(ResourceList):
        schema = ComputerSchema
        data_layer = {'session': db.session,
                      'model': Computer,
                      'methods': {'query': Computer.query,
                                  'before_create_object': before_create_object}}

SQLAlchemy
----------

Required parameters:

    :session: the session used by the data layer
    :model: the model used by the data layer

Optional parameters:

    :id_field: the field used as identifier field instead of the primary key of the model
    :url_field: the name of the parameter in the route to get value to filter with. Instead "id" is used.

By default SQLAlchemy eagerly loads related data specified in the include query string parameter. If you want to disable this feature you must add eagerload_includes: False to the data layer parameters.

Custom data layer
-----------------

As previously mentioned, you can create and use your own data layer.
A custom data layer must inherit from `flask_combo_jsonapi.data_layers.base.Base <https://github.com/AdCombo/flask-combo-jsonapi/blob/master/flask_combo_jsonapi/data_layers/base.py>`_.
You can see the full scope of possibilities of a data layer in this base class.

Usage example:

.. code-block:: python

    from flask_combo_jsonapi import ResourceList
    from your_project.schemas import PersonSchema
    from your_project.data_layers import MyCustomDataLayer

    class PersonList(ResourceList):
        schema = PersonSchema
        data_layer = {'class': MyCustomDataLayer,
                      'param_1': value_1,
                      'param_2': value_2}

.. note::

    All items except "class" in the data_layer dict of the resource manager will be plugged as instance attributes of the data layer. It is easier to use in the data layer.
