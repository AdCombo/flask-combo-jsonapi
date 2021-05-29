.. _quickstart:

Quickstart
==========

.. currentmodule:: flask_combo_jsonapi

It's time to write your first advanced REST API.
This guide assumes you have a working understanding of `Flask <https://flask.palletsprojects.com/en/1.1.x/>`_,
and that you have already installed both Flask and Flask-COMBO-JSONAPI.
If not, then follow the steps in the :ref:`installation` section.

In this section you will learn basic usage of Flask-COMBO-JSONAPI
around a small tutorial that uses the SQLAlchemy data layer.
This tutorial shows you an example of a person and their computers.

Advanced example
-------------

An example of Flask-COMBO-JSONAPI API looks like this:

.. literalinclude:: ../examples/api.py
    :language: python

This example provides the following API:

+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| url                                       | method | endpoint         | action                                                |
+===========================================+========+==================+=======================================================+
| /persons                                  | GET    | person_list      | Retrieve a collection of persons                      |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons                                  | POST   | person_list      | Create a person                                       |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                         | GET    | person_detail    | Retrieve details of a person                          |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                         | PATCH  | person_detail    | Update a person                                       |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>                         | DELETE | person_detail    | Delete a person                                       |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/computers               | GET    | computer_list    | Retrieve a collection computers related to a person   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/computers               | POST   | computer_list    | Create a computer related to a person                 |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | GET    | person_computers | Retrieve relationships between a person and computers |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | POST   | person_computers | Create relationships between a person and computers   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | PATCH  | person_computers | Update relationships between a person and computers   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /persons/<int:id>/relationships/computers | DELETE | person_computers | Delete relationships between a person and computers   |
+--------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers                                | GET    | computer_list    | Retrieve a collection of computers                    |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers                                | POST   | computer_list    | Create a computer                                     |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                       | GET    | computer_detail  | Retrieve details of a computer                        |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                       | PATCH  | computer_detail  | Update a computer                                     |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>                       | DELETE | computer_detail  | Delete a computer                                     |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                 | GET    | person_detail    | Retrieve details of the owner of a computer           |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                 | PATCH  | person_detail    | Update the owner of a computer                        |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/owner                 | DELETE | person_detail    | Delete the owner of a computer                        |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | GET    | person_computers | Retrieve relationships between a person and computers |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | POST   | person_computers | Create relationships between a person and computers   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | PATCH  | person_computers | Update relationships between a person and computers   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+
| /computers/<int:id>/relationships/owner   | DELETE | person_computers | Delete relationships between a person and computers   |
+-------------------------------------------+--------+------------------+-------------------------------------------------------+

.. warning::

    In this example Flask-SQLAlchemy is used, so you'll need to install it before running this example.

    $ pip install flask_sqlalchemy

Save `this file <https://github.com/AdCombo/flask-combo-jsonapi/blob/master/examples/api.py>`_ as api.py and run it using your Python interpreter. Note that we've enabled
`Flask debugging <https://flask.palletsprojects.com/en/2.0.x/quickstart/#debug-mode>`_ mode to provide code reloading and better error
messages. ::

    $ python api.py
     * Running on http://127.0.0.1:5000/
     * Restarting with reloader

.. warning::

    Debug mode should never be used in a production environment!

Classical CRUD operations
-------------------------

Create object
~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_computer
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_computer_result
  :language: HTTP


List objects
~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_computers
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_computers_result
  :language: HTTP


Update object
~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__patch_computer
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__patch_computer_result
  :language: HTTP


Delete object
~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__delete_computer
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__delete_computer_result
  :language: HTTP


Relationships
-------------

| Now let's use relationships tools.
| First, create 3 computers named "Halo", "Nestor" and "Commodore".
|
| Done?
| Ok. So let's continue this tutorial.
|
| We assume that Halo has id=2, Nestor id=3 and Commodore id=4.

Create object with related object(s)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_person_with_computer_relationship
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_person_with_computer_relationship_result
  :language: HTTP


You can see that we have added the query string parameter "include" to the URL

.. sourcecode:: http

    POST /persons?include=computers HTTP/1.1

Thanks to this parameter, the related computers' details are included in the result. If you want to learn more: :ref:`include_related_objects`

Update object and his relationships
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now John sell his Halo (id=2) and buys a new computer named Nestor (id=3).
So we want to link this new computer to John.
John have also made a mistake in his email so let's update these 2 things in the same time.

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__update_person_with_computer_relationship
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__update_person_with_computer_relationship_result
  :language: HTTP


Create relationship
~~~~~~~~~~~~~~~~~~~

Now John buys a new computer named Commodore (id=4) so let's link it to John.

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_computer_relationship_for_person
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__create_computer_relationship_for_person_result
  :language: HTTP


Load person with all the related computers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_person_with_computers
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_person_with_computers_result
  :language: HTTP


Check person's computers without loading actual person
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_person_related_computers
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__get_person_related_computers_result
  :language: HTTP


Delete relationship
~~~~~~~~~~~~~~~~~~~

Now John sells his old Nestor computer, so let's unlink it from John.

Request:

.. literalinclude:: ./http_snippets/snippets/relationship_api__delete_computer_relationship
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/relationship_api__delete_computer_relationship_result
  :language: HTTP


If you want to see more examples visit `JSON API 1.0 specification <http://jsonapi.org/>`_
