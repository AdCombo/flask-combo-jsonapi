"""This module is a CRUD interface between resource managers and the sqlalchemy ORM"""

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import QueryableAttribute
from sqlalchemy.orm import joinedload, ColumnProperty, RelationshipProperty
from marshmallow import class_registry
from marshmallow.base import SchemaABC

from flask import current_app
from flask_combo_jsonapi.data_layers.base import BaseDataLayer
from flask_combo_jsonapi.data_layers.sorting.alchemy import create_sorts
from flask_combo_jsonapi.exceptions import (
    RelationNotFound,
    RelatedObjectNotFound,
    JsonApiException,
    ObjectNotFound,
    InvalidInclude,
    InvalidType,
    PluginMethodNotImplementedError,
)
from flask_combo_jsonapi.data_layers.filtering.alchemy import create_filters
from flask_combo_jsonapi.schema import (
    get_model_field,
    get_related_schema,
    get_relationships,
    get_nested_fields,
    get_schema_field,
)
from flask_combo_jsonapi.utils import SPLIT_REL


class SqlalchemyDataLayer(BaseDataLayer):
    """Sqlalchemy data layer"""

    def __init__(self, kwargs):
        """Initialize an instance of SqlalchemyDataLayer

        :param dict kwargs: initialization parameters of an SqlalchemyDataLayer instance
        """
        super().__init__(kwargs)

        if not hasattr(self, "session"):
            raise Exception(
                f"You must provide a session in data_layer_kwargs to use sqlalchemy data layer in {self.resource.__name__}"
            )
        if not hasattr(self, "model"):
            raise Exception(
                f"You must provide a model in data_layer_kwargs to use sqlalchemy data layer in {self.resource.__name__}"
            )

        self.disable_collection_count: bool = False
        self.default_collection_count: int = -1

    def post_init(self):
        """
        Checking some props here
        :return:
        """
        if self.resource is None:
            # if working outside the resource, it's not assigned here
            return

        if not hasattr(self.resource, "disable_collection_count") or self.resource.disable_collection_count is False:
            return

        params = self.resource.disable_collection_count

        if isinstance(params, (bool, int)):
            self.disable_collection_count = bool(params)

        if isinstance(params, (tuple, list)):
            try:
                self.disable_collection_count, self.default_collection_count = params
            except ValueError:
                raise ValueError(
                    "Resource's attribute `disable_collection_count` "
                    "has to be bool or list/tuple with exactly 2 values!\n"
                    "For example `disable_collection_count = (True, 999)`"
                )
        # just ignoring other types, we don't know how to process them

    def create_object(self, data, view_kwargs):
        """Create an object through sqlalchemy

        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object from sqlalchemy
        """
        for i_plugins in self.resource.plugins:
            try:
                i_plugins.data_layer_before_create_object(data=data, view_kwargs=view_kwargs, self_json_api=self)
            except PluginMethodNotImplementedError:
                pass

        self.before_create_object(data, view_kwargs)

        relationship_fields = get_relationships(self.resource.schema, model_field=True)
        nested_fields = get_nested_fields(self.resource.schema, model_field=True)

        join_fields = relationship_fields + nested_fields

        for i_plugins in self.resource.plugins:
            try:
                data = i_plugins.data_layer_create_object_clean_data(
                    data=data, view_kwargs=view_kwargs, join_fields=join_fields, self_json_api=self,
                )
            except PluginMethodNotImplementedError:
                pass
        obj = self.model(**{key: value for (key, value) in data.items() if key not in join_fields})
        self.apply_relationships(data, obj)
        self.apply_nested_fields(data, obj)

        for i_plugins in self.resource.plugins:
            try:
                i_plugins.data_layer_after_create_object(
                    data=data, view_kwargs=view_kwargs, obj=obj, self_json_api=self,
                )
            except PluginMethodNotImplementedError:
                pass

        self.session.add(obj)
        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException(f"Object creation error: {e}", source={"pointer": "/data"})

        self.after_create_object(obj, data, view_kwargs)

        return obj

    def get_object(self, view_kwargs, qs=None):
        """Retrieve an object through sqlalchemy

        :params dict view_kwargs: kwargs from the resource view
        :return DeclarativeMeta: an object from sqlalchemy
        """
        # Нужно выталкивать из sqlalchemy Закешированные запросы, иначе не удастся загрузить данные о current_user
        self.session.expire_all()

        self.before_get_object(view_kwargs)

        id_field = getattr(self, "id_field", inspect(self.model).primary_key[0].key)
        try:
            filter_field = getattr(self.model, id_field)
        except Exception:
            raise Exception(f"{self.model.__name__} has no attribute {id_field}")

        url_field = getattr(self, "url_field", "id")
        filter_value = view_kwargs[url_field]

        query = self.retrieve_object_query(view_kwargs, filter_field, filter_value)

        if self.resource is not None:
            for i_plugins in self.resource.plugins:
                try:
                    query = i_plugins.data_layer_get_object_update_query(
                        query=query, qs=qs, view_kwargs=view_kwargs, self_json_api=self,
                    )
                except PluginMethodNotImplementedError:
                    pass

        if qs is not None:
            query = self.eagerload_includes(query, qs)

        try:
            obj = query.one()
        except NoResultFound:
            obj = None

        self.after_get_object(obj, view_kwargs)

        return obj

    def get_collection_count(self, query, qs, view_kwargs) -> int:
        """
        :param query: SQLAlchemy query
        :param qs: QueryString
        :param view_kwargs: view kwargs
        :return:
        """
        if self.disable_collection_count is True:
            return self.default_collection_count

        return query.count()

    def get_collection(self, qs, view_kwargs):
        """Retrieve a collection of objects through sqlalchemy

        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param dict view_kwargs: kwargs from the resource view
        :return tuple: the number of object and the list of objects
        """
        # Нужно выталкивать из sqlalchemy Закешированные запросы, иначе не удастся загрузить данные о current_user
        self.session.expire_all()

        self.before_get_collection(qs, view_kwargs)

        query = self.query(view_kwargs)

        for i_plugins in self.resource.plugins:
            try:
                query = i_plugins.data_layer_get_collection_update_query(
                    query=query, qs=qs, view_kwargs=view_kwargs, self_json_api=self,
                )
            except PluginMethodNotImplementedError:
                pass

        if qs.filters:
            query = self.filter_query(query, qs.filters, self.model)

        if qs.sorting:
            query = self.sort_query(query, qs.sorting)

        objects_count = self.get_collection_count(query, qs, view_kwargs)

        if getattr(self, "eagerload_includes", True):
            query = self.eagerload_includes(query, qs)

        query = self.paginate_query(query, qs.pagination)

        collection = query.all()

        collection = self.after_get_collection(collection, qs, view_kwargs)

        return objects_count, collection

    def update_object(self, obj, data, view_kwargs):
        """Update an object through sqlalchemy

        :param DeclarativeMeta obj: an object from sqlalchemy
        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if object have changed else False
        """
        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        self.before_update_object(obj, data, view_kwargs)

        relationship_fields = get_relationships(self.resource.schema, model_field=True)
        nested_fields = get_nested_fields(self.resource.schema, model_field=True)

        join_fields = relationship_fields + nested_fields

        for i_plugins in self.resource.plugins:
            try:
                data = i_plugins.data_layer_update_object_clean_data(
                    data=data, obj=obj, view_kwargs=view_kwargs, join_fields=join_fields, self_json_api=self,
                )
            except PluginMethodNotImplementedError:
                pass

        for key, value in data.items():
            if hasattr(obj, key) and key not in join_fields:
                setattr(obj, key, value)

        self.apply_relationships(data, obj)
        self.apply_nested_fields(data, obj)

        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            orig_e = getattr(e, "orig", object)
            message = getattr(orig_e, "args", [])
            message = message[0] if message else None
            e = message if message else e
            raise JsonApiException("Update object error: " + str(e), source={"pointer": "/data"})

        self.after_update_object(obj, data, view_kwargs)

    def delete_object(self, obj, view_kwargs):
        """Delete an object through sqlalchemy

        :param DeclarativeMeta item: an item from sqlalchemy
        :param dict view_kwargs: kwargs from the resource view
        """
        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        self.before_delete_object(obj, view_kwargs)

        for i_plugins in self.resource.plugins:
            try:
                i_plugins.data_layer_delete_object_clean_data(obj=obj, view_kwargs=view_kwargs, self_json_api=self)
            except PluginMethodNotImplementedError:
                pass

        self.session.delete(obj)
        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Delete object error: " + str(e))

        self.after_delete_object(obj, view_kwargs)

    def create_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Create a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        self.before_create_relationship(json_data, relationship_field, related_id_field, view_kwargs)

        obj = self.get_object(view_kwargs)

        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        if not hasattr(obj, relationship_field):
            raise RelationNotFound(f"{obj.__class__.__name__} has no attribute {relationship_field}")

        related_model = getattr(obj.__class__, relationship_field).property.mapper.class_

        updated = False

        if isinstance(json_data["data"], list):
            obj_ids = {str(getattr(obj__, related_id_field)) for obj__ in getattr(obj, relationship_field)}

            for obj_ in json_data["data"]:
                if obj_["id"] not in obj_ids:
                    getattr(obj, relationship_field).append(
                        self.get_related_object(related_model, related_id_field, obj_)
                    )
                    updated = True
        else:
            related_object = None

            if json_data["data"] is not None:
                related_object = self.get_related_object(related_model, related_id_field, json_data["data"])

            obj_id = getattr(getattr(obj, relationship_field), related_id_field, None)
            new_obj_id = getattr(related_object, related_id_field, None)
            if obj_id != new_obj_id:
                setattr(obj, relationship_field, related_object)
                updated = True

        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Create relationship error: " + str(e))

        self.after_create_relationship(obj, updated, json_data, relationship_field, related_id_field, view_kwargs)

        return obj, updated

    def get_relationship(self, relationship_field, related_type_, related_id_field, view_kwargs):
        """Get a relationship

        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        self.before_get_relationship(relationship_field, related_type_, related_id_field, view_kwargs)

        obj = self.get_object(view_kwargs)

        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        if not hasattr(obj, relationship_field):
            raise RelationNotFound(f"{obj.__class__.__name__} has no attribute {relationship_field}")

        related_objects = getattr(obj, relationship_field)

        if related_objects is None:
            return obj, related_objects

        self.after_get_relationship(
            obj, related_objects, relationship_field, related_type_, related_id_field, view_kwargs,
        )

        if isinstance(related_objects, InstrumentedList):
            return obj, [{"type": related_type_, "id": getattr(obj_, related_id_field)} for obj_ in related_objects]
        else:
            return obj, {"type": related_type_, "id": getattr(related_objects, related_id_field)}

    def update_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Update a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        self.before_update_relationship(json_data, relationship_field, related_id_field, view_kwargs)

        obj = self.get_object(view_kwargs)

        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        if not hasattr(obj, relationship_field):
            raise RelationNotFound(f"{obj.__class__.__name__} has no attribute {relationship_field}")

        related_model = getattr(obj.__class__, relationship_field).property.mapper.class_

        updated = False

        if isinstance(json_data["data"], list):
            related_objects = []

            for obj_ in json_data["data"]:
                related_objects.append(self.get_related_object(related_model, related_id_field, obj_))

            obj_ids = {getattr(obj__, related_id_field) for obj__ in getattr(obj, relationship_field)}
            new_obj_ids = {getattr(related_object, related_id_field) for related_object in related_objects}
            if obj_ids != new_obj_ids:
                setattr(obj, relationship_field, related_objects)
                updated = True

        else:
            related_object = None

            if json_data["data"] is not None:
                related_object = self.get_related_object(related_model, related_id_field, json_data["data"])

            obj_id = getattr(getattr(obj, relationship_field), related_id_field, None)
            new_obj_id = getattr(related_object, related_id_field, None)
            if obj_id != new_obj_id:
                setattr(obj, relationship_field, related_object)
                updated = True

        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Update relationship error: " + str(e))

        self.after_update_relationship(obj, updated, json_data, relationship_field, related_id_field, view_kwargs)

        return obj, updated

    def delete_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Delete a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        """
        self.before_delete_relationship(json_data, relationship_field, related_id_field, view_kwargs)

        obj = self.get_object(view_kwargs)

        if obj is None:
            url_field = getattr(self, "url_field", "id")
            filter_value = view_kwargs[url_field]
            raise ObjectNotFound(f"{self.model.__name__}: {filter_value} not found", source={"parameter": url_field})

        if not hasattr(obj, relationship_field):
            raise RelationNotFound(f"{obj.__class__.__name__} has no attribute {relationship_field}")

        related_model = getattr(obj.__class__, relationship_field).property.mapper.class_

        updated = False

        if isinstance(json_data["data"], list):
            obj_ids = {str(getattr(obj__, related_id_field)) for obj__ in getattr(obj, relationship_field)}

            for obj_ in json_data["data"]:
                if obj_["id"] in obj_ids:
                    getattr(obj, relationship_field).remove(
                        self.get_related_object(related_model, related_id_field, obj_)
                    )
                    updated = True
        else:
            setattr(obj, relationship_field, None)
            updated = True

        try:
            self.session.commit()
        except JsonApiException as e:
            self.session.rollback()
            raise e
        except Exception as e:
            self.session.rollback()
            raise JsonApiException("Delete relationship error: " + str(e))

        self.after_delete_relationship(obj, updated, json_data, relationship_field, related_id_field, view_kwargs)

        return obj, updated

    def get_related_object(self, related_model, related_id_field, obj):
        """Get a related object

        :param Model related_model: an sqlalchemy model
        :param str related_id_field: the identifier field of the related model
        :param DeclarativeMeta obj: the sqlalchemy object to retrieve related objects from
        :return DeclarativeMeta: a related object
        """
        try:
            related_object = (
                self.session.query(related_model).filter(getattr(related_model, related_id_field) == obj["id"]).one()
            )
        except NoResultFound:
            raise RelatedObjectNotFound(f"{related_model.__name__}.{related_id_field}: {obj['id']} not found")

        return related_object

    def apply_relationships(self, data, obj):
        """Apply relationship provided by data to obj

        :param dict data: data provided by the client
        :param DeclarativeMeta obj: the sqlalchemy object to plug relationships to
        :return boolean: True if relationship have changed else False
        """
        relationships_to_apply = []
        relationship_fields = get_relationships(self.resource.schema, model_field=True)
        for key, value in data.items():
            if key in relationship_fields:
                related_model = getattr(obj.__class__, key).property.mapper.class_
                schema_field = get_schema_field(self.resource.schema, key)
                related_id_field = self.resource.schema._declared_fields[schema_field].id_field

                if isinstance(value, list):
                    related_objects = []

                    for identifier in value:
                        related_object = self.get_related_object(related_model, related_id_field, {"id": identifier})
                        related_objects.append(related_object)

                    relationships_to_apply.append({"field": key, "value": related_objects})
                else:
                    related_object = None

                    if value is not None:
                        related_object = self.get_related_object(related_model, related_id_field, {"id": value})

                    relationships_to_apply.append({"field": key, "value": related_object})

        for relationship in relationships_to_apply:
            setattr(obj, relationship["field"], relationship["value"])

    def apply_nested_fields(self, data, obj):
        nested_fields_to_apply = []
        nested_fields = get_nested_fields(self.resource.schema, model_field=True)
        for key, value in data.items():
            if key in nested_fields:
                nested_field_inspection = inspect(getattr(obj.__class__, key))

                if not isinstance(nested_field_inspection, QueryableAttribute):
                    raise InvalidType("Unrecognized nested field type: not a queryable attribute.")

                if isinstance(nested_field_inspection.property, RelationshipProperty):
                    nested_model = getattr(obj.__class__, key).property.mapper.class_

                    if isinstance(value, list):
                        nested_objects = []

                        for identifier in value:
                            nested_object = nested_model(**identifier)
                            nested_objects.append(nested_object)

                        nested_fields_to_apply.append({"field": key, "value": nested_objects})
                    else:
                        nested_fields_to_apply.append({"field": key, "value": nested_model(**value)})
                elif isinstance(nested_field_inspection.property, ColumnProperty):
                    nested_fields_to_apply.append({"field": key, "value": value})
                else:
                    raise InvalidType("Unrecognized nested field type: not a RelationshipProperty or ColumnProperty.")

        for nested_field in nested_fields_to_apply:
            setattr(obj, nested_field["field"], nested_field["value"])

    def filter_query(self, query, filter_info, model):
        """Filter query according to jsonapi 1.0

        :param Query query: sqlalchemy query to sort
        :param filter_info: filter information
        :type filter_info: dict or None
        :param DeclarativeMeta model: an sqlalchemy model
        :return Query: the sorted query
        """
        if filter_info:
            filters, joins = create_filters(model, filter_info, self.resource)
            for i_join in joins:
                query = query.join(*i_join)
            query = query.filter(*filters)

        return query

    def sort_query(self, query, sort_info):
        """Sort query according to jsonapi 1.0

        :param Query query: sqlalchemy query to sort
        :param list sort_info: sort information
        :return Query: the sorted query
        """
        if sort_info:
            sorts, joins = create_sorts(self.model, sort_info, self.resource if hasattr(self, "resource") else None)
            for i_join in joins:
                query = query.join(*i_join)
            for i_sort in sorts:
                query = query.order_by(i_sort)
        return query

    def paginate_query(self, query, paginate_info):
        """Paginate query according to jsonapi 1.0

        :param Query query: sqlalchemy queryset
        :param dict paginate_info: pagination information
        :return Query: the paginated query
        """
        if int(paginate_info.get("size", 1)) == 0:
            return query

        page_size = int(paginate_info.get("size", 0)) or current_app.config["PAGE_SIZE"]
        query = query.limit(page_size)
        if paginate_info.get("number"):
            query = query.offset((int(paginate_info["number"]) - 1) * page_size)

        return query

    def eagerload_includes(self, query, qs):
        """Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter

        :param Query query: sqlalchemy queryset
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :return Query: the query with includes eagerloaded
        """
        for include in qs.include:
            joinload_object = None

            if SPLIT_REL in include:
                current_schema = self.resource.schema
                for obj in include.split(SPLIT_REL):
                    try:
                        field = get_model_field(current_schema, obj)
                    except Exception as e:
                        raise InvalidInclude(str(e))

                    if joinload_object is None:
                        joinload_object = joinedload(field)
                    else:
                        joinload_object = joinload_object.joinedload(field)

                    related_schema_cls = get_related_schema(current_schema, obj)

                    if isinstance(related_schema_cls, SchemaABC):
                        related_schema_cls = related_schema_cls.__class__
                    else:
                        related_schema_cls = class_registry.get_class(related_schema_cls)

                    current_schema = related_schema_cls
            else:
                try:
                    field = get_model_field(self.resource.schema, include)
                except Exception as e:
                    raise InvalidInclude(str(e))

                joinload_object = joinedload(field)

            query = query.options(joinload_object)

        return query

    def retrieve_object_query(self, view_kwargs, filter_field, filter_value):
        """Build query to retrieve object

        :param dict view_kwargs: kwargs from the resource view
        :params sqlalchemy_field filter_field: the field to filter on
        :params filter_value: the value to filter with
        :return sqlalchemy query: a query from sqlalchemy
        """
        return self.session.query(self.model).filter(filter_field == filter_value)

    def query(self, view_kwargs):
        """Construct the base query to retrieve wanted data

        :param dict view_kwargs: kwargs from the resource view
        """
        return self.session.query(self.model)

    def before_create_object(self, data, view_kwargs):
        """Provide additional data before object creation

        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_create_object(self, obj, data, view_kwargs):
        """Provide additional data after object creation

        :param obj: an object from data layer
        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def before_get_object(self, view_kwargs):
        """Make work before to retrieve an object

        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_get_object(self, obj, view_kwargs):
        """Make work after to retrieve an object

        :param obj: an object from data layer
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def before_get_collection(self, qs, view_kwargs):
        """Make work before to retrieve a collection of objects

        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_get_collection(self, collection, qs, view_kwargs):
        """Make work after to retrieve a collection of objects

        :param iterable collection: the collection of objects
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param dict view_kwargs: kwargs from the resource view
        """
        return collection

    def before_update_object(self, obj, data, view_kwargs):
        """Make checks or provide additional data before update object

        :param obj: an object from data layer
        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_update_object(self, obj, data, view_kwargs):
        """Make work after update object

        :param obj: an object from data layer
        :param dict data: the data validated by marshmallow
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def before_delete_object(self, obj, view_kwargs):
        """Make checks before delete object

        :param obj: an object from data layer
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_delete_object(self, obj, view_kwargs):
        """Make work after delete object

        :param obj: an object from data layer
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def before_create_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work before to create a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        pass

    def after_create_relationship(self, obj, updated, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work after to create a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        pass

    def before_get_relationship(self, relationship_field, related_type_, related_id_field, view_kwargs):
        """Make work before to get information about a relationship

        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        pass

    def after_get_relationship(
        self, obj, related_objects, relationship_field, related_type_, related_id_field, view_kwargs,
    ):
        """Make work after to get information about a relationship

        :param obj: an object from data layer
        :param iterable related_objects: related objects of the object
        :param str relationship_field: the model attribute used for relationship
        :param str related_type_: the related resource type
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return tuple: the object and related object(s)
        """
        pass

    def before_update_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work before to update a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        pass

    def after_update_relationship(self, obj, updated, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work after to update a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        :return boolean: True if relationship have changed else False
        """
        pass

    def before_delete_relationship(self, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work before to delete a relationship

        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        """
        pass

    def after_delete_relationship(self, obj, updated, json_data, relationship_field, related_id_field, view_kwargs):
        """Make work after to delete a relationship

        :param obj: an object from data layer
        :param bool updated: True if object was updated else False
        :param dict json_data: the request params
        :param str relationship_field: the model attribute used for relationship
        :param str related_id_field: the identifier field of the related model
        :param dict view_kwargs: kwargs from the resource view
        """
        pass
