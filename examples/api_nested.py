from flask import Flask
from sqlalchemy import UniqueConstraint

from flask_combo_jsonapi import Api, ResourceDetail, ResourceList, ResourceRelationship
from flask_combo_jsonapi.data_layers.alchemy import SqlalchemyDataLayer
from flask_combo_jsonapi.exceptions import ObjectNotFound
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound
from marshmallow_jsonapi.flask import Schema, Relationship
from marshmallow import Schema as MarshmallowSchema, pre_load
from marshmallow_jsonapi import fields

# Create the Flask application
app = Flask(__name__)
app.config['DEBUG'] = True

# Initialize SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/api_nested.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Create data storage
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    password = db.Column(db.String)
    tags = db.relationship("PersonTag", cascade="save-update, merge, delete, delete-orphan")
    single_tag = db.relationship(
        "PersonSingleTag",
        uselist=False,
        cascade="save-update, merge, delete, delete-orphan",
    )
    json_data = db.Column(db.JSON)


class Computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person', backref=db.backref('computers'))


class PersonTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), index=True)
    key = db.Column(db.String)
    value = db.Column(db.String)

    __table_args__ = (
        UniqueConstraint(
            'person_id',
            'key',
            'value',
            name='_person_key_value'
        ),
    )


class PersonSingleTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), index=True)
    key = db.Column(db.String)
    value = db.Column(db.String)

    __table_args__ = (
        UniqueConstraint(
            'person_id',
            'key',
            'value',
            name='_person_key_value'
        ),
    )


db.create_all()


# Create schema
class PersonTagSchema(MarshmallowSchema):
    class Meta:
        type_ = 'person_tag'

    id = fields.String(dump_only=True, load_only=True)
    key = fields.String()
    value = fields.String()


class PersonSingleTagSchema(MarshmallowSchema):
    class Meta:
        type_ = 'person_single_tag'

    id = fields.String(dump_only=True, load_only=True)
    key = fields.String()
    value = fields.String()


# Create logical data abstraction (same as data storage for this first example)
class PersonSchema(Schema):
    class Meta:
        type_ = 'person'
        self_view = 'person_detail'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'person_list'

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.String(required=True)
    email = fields.Email(load_only=True)
    display_name = fields.Function(lambda obj: "{} <{}>".format(obj.name.upper(), obj.email))
    tags = fields.Nested(PersonTagSchema, many=True)
    single_tag = fields.Nested(PersonSingleTagSchema, many=False)
    json_data = fields.Dict(dump_only=True)
    computers = Relationship(
        self_view='person_computers',
        self_view_kwargs={'id': '<id>'},
        related_view='computer_list',
        related_view_kwargs={'id': '<id>'},
        many=True,
        schema='ComputerSchema',
        type_='computer',
    )

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


class ComputerSchema(Schema):
    class Meta:
        type_ = 'computer'
        self_view = 'computer_detail'
        self_view_kwargs = {'id': '<id>'}

    id = fields.Integer(as_string=True, dump_only=True)
    serial = fields.String(required=True)
    owner = Relationship(
        attribute='person',
        self_view='computer_person',
        self_view_kwargs={'id': '<id>'},
        related_view='person_detail',
        related_view_kwargs={'computer_id': '<id>'},
        schema='PersonSchema',
        type_='person',
    )

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


class PersonDetailSqlalchemyDataLayer(SqlalchemyDataLayer):

    def before_get_object(self, view_kwargs):
        if not view_kwargs.get('computer_id'):
            return
        try:
            computer = self.session.query(Computer).filter_by(
                id=view_kwargs['computer_id'],
            ).one()
        except NoResultFound:
            raise ObjectNotFound(
                "Computer: {} not found".format(view_kwargs['computer_id']),
                source={'parameter': 'computer_id'},
             )
        else:
            if computer.person is not None:
                view_kwargs['id'] = computer.person.id
            else:
                view_kwargs['id'] = None


class PersonDetail(ResourceDetail):
    schema = PersonSchema
    data_layer = {
        'session': db.session,
        'model': Person,
        'class': PersonDetailSqlalchemyDataLayer,
    }


class PersonRelationship(ResourceRelationship):
    schema = PersonSchema
    data_layer = {
        'session': db.session,
        'model': Person
    }


class RelatedComputersSqlalchemyDataLayer(SqlalchemyDataLayer):

    def query(self, view_kwargs):
        query_ = self.session.query(Computer)
        if view_kwargs.get('id') is not None:
            try:
                self.session.query(Person).filter_by(id=view_kwargs['id']).one()
            except NoResultFound:
                raise ObjectNotFound(
                    "Person: {} not found".format(view_kwargs['id']),
                    source={'parameter': 'id'},
                )
            else:
                query_ = query_.join(Person).filter(Person.id == view_kwargs['id'])
        return query_

    def before_create_object(self, data, view_kwargs):
        if view_kwargs.get('id') is not None:
            person = self.session.query(Person).filter_by(id=view_kwargs['id']).one()
            data['person_id'] = person.id


class ComputerList(ResourceList):
    schema = ComputerSchema
    data_layer = {
        'session': db.session,
        'model': Computer,
        'class': RelatedComputersSqlalchemyDataLayer,
    }


class ComputerDetail(ResourceDetail):
    schema = ComputerSchema
    data_layer = {
        'session': db.session,
        'model': Computer,
    }


class ComputerRelationship(ResourceRelationship):
    schema = ComputerSchema
    data_layer = {
        'session': db.session,
        'model': Computer,
    }


# Create endpoints
api = Api(app)

api.route(PersonList, 'person_list', '/persons')
api.route(PersonDetail, 'person_detail', '/persons/<int:id>', '/computers/<int:computer_id>/owner')
api.route(PersonRelationship, 'person_computers', '/persons/<int:id>/relationships/computers')
api.route(ComputerList, 'computer_list', '/computers', '/persons/<int:id>/computers')
api.route(ComputerDetail, 'computer_detail', '/computers/<int:id>')
api.route(ComputerRelationship, 'computer_person', '/computers/<int:id>/relationships/owner')

if __name__ == '__main__':
    # Start application
    app.run(debug=True)
