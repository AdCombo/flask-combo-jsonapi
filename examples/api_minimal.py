from flask import Flask
from marshmallow import pre_load

from flask_combo_jsonapi import Api, ResourceDetail, ResourceList
from flask_sqlalchemy import SQLAlchemy
from marshmallow_jsonapi.flask import Schema
from marshmallow_jsonapi import fields

# Create the Flask application and the Flask-SQLAlchemy object.
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/api_minimal.db'
db = SQLAlchemy(app)


# Create model
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


# Create the database.
db.create_all()


# Create schema
class PersonSchema(Schema):
    class Meta:
        type_ = 'person'
        self_view = 'person_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'person_list'

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.String()

    @pre_load
    def remove_id_before_deserializing(self, data, **kwargs):
        """
        We don't want to allow editing ID on POST / PATCH

        Related issues:
        https://github.com/AdCombo/flask-combo-jsonapi/issues/34
        https://github.com/miLibris/flask-rest-jsonapi/issues/193
        """
        if 'id' in data:
            del data['id']
        return data


# Create resource managers
class PersonList(ResourceList):
    schema = PersonSchema
    data_layer = {
        'session': db.session,
        'model': Person,
    }


class PersonDetail(ResourceDetail):
    schema = PersonSchema
    data_layer = {
        'session': db.session,
        'model': Person,
    }


# Create the API object
api = Api(app)
api.route(PersonList, 'person_list', '/persons')
api.route(PersonDetail, 'person_detail', '/persons/<int:id>')

# Start the flask loop
if __name__ == '__main__':
    app.run()
