.. image:: https://github.com/AdCombo/flask-combo-jsonapi/workflows/Python%20tests%20and%20coverage/badge.svg
   :alt: flask-combo-jsonapi actions
   :target: https://github.com/AdCombo/flask-combo-jsonapi/actions
.. image:: https://coveralls.io/repos/github/AdCombo/flask-combo-jsonapi/badge.svg
   :alt: flask-combo-jsonapi coverage
   :target: https://coveralls.io/github/AdCombo/flask-combo-jsonapi
.. image:: https://img.shields.io/pypi/v/flask-combo-jsonapi.svg
   :alt: PyPI
   :target: http://pypi.org/p/flask-combo-jsonapi


Flask-COMBO-JSONAPI
###################

Flask-COMBO-JSONAPI is a flask extension for building REST APIs. It combines the power of `Flask-Restless <https://flask-restless.readthedocs.io/>`_ and the flexibility of `Flask-RESTful <https://flask-restful.readthedocs.io/>`_ around a strong specification `JSONAPI 1.0 <http://jsonapi.org/>`_. This framework is designed to quickly build REST APIs and fit the complexity of real life projects with legacy data and multiple data storages.

The main goal is to make it flexible using `plugin system <https://combojsonapi.readthedocs.io/>`_


Install
=======

    pip install Flask-COMBO-JSONAPI



.. include:: ./docs/minimal_api_head.rst


Flask-COMBO-JSONAPI vs `Flask-RESTful <https://flask-restful.readthedocs.io/en/latest/>`_
==========================================================================================

* In contrast to Flask-RESTful, Flask-COMBO-JSONAPI provides a default implementation of get, post, patch and delete methods around a strong specification JSONAPI 1.0. Thanks to this you can build REST API very quickly.
* Flask-COMBO-JSONAPI is as flexible as Flask-RESTful. You can rewrite every default method implementation to make custom work like distributing object creation.

Flask-COMBO-JSONAPI vs `Flask-Restless <https://flask-restless.readthedocs.io/en/stable/>`_
==========================================================================================

* Flask-COMBO-JSONAPI is a real implementation of JSONAPI 1.0 specification. So in contrast to Flask-Restless, Flask-COMBO-JSONAPI forces you to create a real logical abstration over your data models with `Marshmallow <https://marshmallow.readthedocs.io/en/latest/>`_. So you can create complex resource over your data.
* In contrast to Flask-Restless, Flask-COMBO-JSONAPI can use any ORM or data storage through the data layer concept, not only `SQLAlchemy <http://www.sqlalchemy.org/>`_. A data layer is a CRUD interface between your resource and one or more data storage so you can fetch data from any data storage of your choice or create resource that use multiple data storages.
* Like I said previously, Flask-COMBO-JSONAPI is a real implementation of JSONAPI 1.0 specification. So in contrast to Flask-Restless you can manage relationships via REST. You can create dedicated URL to create a CRUD API to manage relationships.
* Plus Flask-COMBO-JSONAPI helps you to design your application with strong separation between resource definition (schemas), resource management (resource class) and route definition to get a great organization of your source code.
* In contrast to Flask-Restless, Flask-COMBO-JSONAPI is highly customizable. For example you can entirely customize your URLs, define multiple URLs for the same resource manager, control serialization parameters of each method and lots of very useful parameters.
* Finally in contrast to Flask-Restless, Flask-COMBO-JSONAPI provides a great error handling system according to JSONAPI 1.0. Plus the exception handling system really helps the API developer to quickly find missing resources requirements.

Documentation
=============

Documentation available here: https://flask-combo-jsonapi.readthedocs.io/

Thanks
======

Flask, marshmallow, marshmallow_jsonapi, sqlalchemy, Flask-RESTful and Flask-Restless are awesome projects. These libraries gave me inspiration to create Flask-COMBO-JSONAPI, so huge thanks to authors and contributors.
