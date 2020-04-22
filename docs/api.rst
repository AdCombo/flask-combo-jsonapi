.. _api:

Api
===

.. currentmodule:: flask_combo_jsonapi

You can provide global decorators as tuple to the Api.

Example:

.. code-block:: python

    from flask_combo_jsonapi import Api
    from your_project.security import login_required

    api = Api(decorators=(login_required,))
