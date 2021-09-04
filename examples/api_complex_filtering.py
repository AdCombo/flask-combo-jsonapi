from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_combo_jsonapi import Api, ResourceDetail, ResourceList
from sqlalchemy import String, func, Integer, Float
from sqlalchemy.dialects.postgresql import ARRAY
from marshmallow_jsonapi.flask import Schema
from marshmallow_jsonapi import fields


# SCHEMAS
TYPE_MAP = {
    int: Integer,
    float: Float,
    str: String,
}


class BaseInSqlFiltering:
    def _in_sql_filter_(self, marshmallow_field, model_column, value, operator):
        """
        Create sqlalchemy filter 'in'
        :param marshmallow_field:
        :param model_column: (sqlalchemy column)
        :param value: filter value
        :param operator: operator: "eq", "in"...
        :return:
        """
        raise NotImplementedError

    def _in__sql_filter_(self, *args, **kwargs):
        return self._in_sql_filter_(*args, **kwargs)

    def _notin_sql_filter_(self, *args, **kwargs):
        """
        Invert filter in
        :param marshmallow_field:
        :param model_column:
        :param value:
        :param operator:
        :return:
        """
        return ~self._in_sql_filter_(*args, **kwargs)

    def _notin__sql_filter_(self, *args, **kwargs):
        return self._notin_sql_filter_(*args, **kwargs)


class ListFieldBase(fields.List, BaseInSqlFiltering):
    def __init__(self, *args, **kwargs):
        # self.container = args[0]
        super().__init__(*args, **kwargs)


class ListField(ListFieldBase):
    def _in_sql_filter_(self, marshmallow_field, model_column, value, operator):
        """
        Create sqlalchemy filter 'in' for array
        :param marshmallow_field:
        :param model_column:
        :param value:
        :param operator:
        :return:
        """
        value = value if isinstance(value, list) else [value]
        value_type = type(value[0])
        if isinstance(model_column.type, ARRAY):
            value = func.cast(value, ARRAY(TYPE_MAP.get(value_type, String)))
        return model_column.op("&&")(value)

    def _ilike_in_str_array_sql_filter_(self, model_column, value, **kwargs):
        return func.array_to_string(model_column, '|').ilike(f'%{value}%')

# // SCHEMAS

# flask app


# Create the Flask application and the Flask-SQLAlchemy object.
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postgres@localhost:5432/postgres'
db = SQLAlchemy(app)


# Create model
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    words = db.Column(db.ARRAY(db.TEXT))


# Create schema
class PersonSchema(Schema):
    class Meta:
        type_ = 'person'
        self_view = 'person_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'person_list'

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.String()
    words = ListField(fields.String())


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


@app.route("/create-persons")
def create_persons():
    # Create tables
    db.create_all()

    # create persons
    db.session.add(Person(name="John", words=["foo", "bar", "green-grass"]))
    db.session.add(Person(name="Sam", words=["spam", "eggs", "green-apple"]))
    db.session.commit()
    return {"message": "ok"}


# Create the API object
api = Api(app)
api.route(PersonList, 'person_list', '/persons')
api.route(PersonDetail, 'person_detail', '/persons/<int:id>')

# Start the flask loop
if __name__ == '__main__':
    app.run()
