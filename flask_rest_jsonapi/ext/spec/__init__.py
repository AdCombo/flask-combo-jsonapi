from copy import deepcopy
from typing import Dict, Any, Set, List, Union, Tuple

from apispec import APISpec
from apispec.exceptions import APISpecError
from apispec.ext.marshmallow import MarshmallowPlugin, OpenAPIConverter, make_schema_key, \
    resolve_schema_instance
from flask_rest_jsonapi import Api
from flask_rest_jsonapi.ext.spec.apispec import DocBlueprintMixin
from flask_rest_jsonapi.ext.spec.compat import APISPEC_VERSION_MAJOR
from flask_rest_jsonapi.ext.spec.plugins_for_apispec import RestfulPlugin
from flask_rest_jsonapi.marshmallow_fields import Relationship
from flask_rest_jsonapi.plugin import BasePlugin
from flask_rest_jsonapi.resource import ResourceList, ResourceDetail
from flask_rest_jsonapi.utils import create_schema_name
from marshmallow import fields, Schema


class ApiSpecPlugin(BasePlugin, DocBlueprintMixin):
    """Плагин для связки json_api и swagger"""
    def __init__(self, app=None, spec_kwargs=None, decorators=None, tags: Dict[str, str] = None):
        """

        :param spec_kwargs:
        :param decorators:
        :param tags: {'<name tag>': '<description tag>'}
        """
        self.decorators_for_autodoc = decorators or tuple()
        self.spec_kwargs = spec_kwargs if spec_kwargs is not None else {}
        self.spec = None
        self.spec_tag = {}
        self.spec_schemas = {}
        self.app = None
        self._fields = []
        # Use lists to enforce order
        self._definitions = []
        self._fields = []
        self._converters = []

        # Инициализация ApiSpec
        self.app = app
        self._app = app
        # Initialize spec
        openapi_version = app.config.get('OPENAPI_VERSION', '2.0')
        openapi_major_version = int(openapi_version.split('.')[0])
        if openapi_major_version < 3:
            base_path = app.config.get('APPLICATION_ROOT')
            # Don't pass basePath if '/' to avoid a bug in apispec
            # https://github.com/marshmallow-code/apispec/issues/78#issuecomment-431854606
            # TODO: Remove this condition when the bug is fixed
            if base_path != '/':
                self.spec_kwargs.setdefault('basePath', base_path)
        self.spec_kwargs.update(app.config.get('API_SPEC_OPTIONS', {}))
        self.spec = APISpec(
            app.name,
            app.config.get('API_VERSION', '1'),
            openapi_version=openapi_version,
            plugins=[MarshmallowPlugin(), RestfulPlugin()],
            **self.spec_kwargs,
        )

        tags = tags if tags else {}
        for tag_name, tag_description in tags.items():
            self.spec_tag[tag_name] = {'name': tag_name, 'description': tag_description, 'add_in_spec': False}
            self._add_tags_in_spec(self.spec_tag[tag_name])

    def after_init_plugin(self, *args, app=None, **kwargs):
        # Register custom fields in spec
        for args in self._fields:
            self.spec.register_field(*args)
        # Register schema definitions in spec
        for name, schema_cls, kwargs in self._definitions:
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(create_schema_name(schema=schema_cls), schema=schema_cls, **kwargs)
            else:
                self.spec.components.schema(create_schema_name(schema=schema_cls), schema=schema_cls, **kwargs)
        # Register custom converters in spec
        for args in self._converters:
            self.spec.register_converter(*args)

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

    def after_route(self,
                    resource: Union[ResourceList, ResourceDetail] = None,
                    view=None,
                    urls: Tuple[str] = None,
                    self_json_api: Api = None,
                    tag: str = None,
                    default_parameters=None,
                    default_schema: Schema = None,
                    **kwargs) -> None:
        """

        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param str tag: тег под которым стоит связать этот ресурс
        :param default_parameters: дефолтные поля для ресурса в сваггер (иначе просто инициализируется [])
        :param Schema default_schema: схема, которая подставиться вместо схемы в стили json api
        :param kwargs:
        :return:
        """
        # Register views in API documentation for this resource
        # resource.register_views_in_doc(self._app, self.spec)
        # Add tag relative to this resource to the global tag list

        # We add definitions (models) to the apiscpec
        if resource.schema:
            self._add_definitions_in_spec(resource.schema)

        # We add tags to the apiscpec
        tag_name = view.title()
        if tag is None and view.title() not in self.spec_tag:
            dict_tag = {'name': view.title(), 'description': '', 'add_in_spec': False}
            self.spec_tag[dict_tag['name']] = dict_tag
            self._add_tags_in_spec(dict_tag)
        elif tag:
            tag_name = self.spec_tag[tag]['name']

        urls = urls if urls else tuple()
        for i_url in urls:
            self._add_paths_in_spec(
                path=i_url,
                resource=resource,
                default_parameters=default_parameters,
                default_schema=default_schema,
                tag_name=tag_name,
                **kwargs
            )

    def _add_paths_in_spec(self, path: str = '', resource: Any = None, tag_name: str = '',
                           default_parameters: List = None,
                           default_schema: Schema = None, **kwargs) -> None:
        operations = {}
        methods: Set[str] = {i_method.lower() for i_method in resource.methods}
        operations_all: Dict[str, Any] = {
            'tags': [tag_name],
            'produces': [
                'application/json'
            ],
            'parameters': default_parameters if default_parameters else []
        }

        parameter_id = {
            "in": "path",
            "name": "id",
            "required": True,
            "type": "integer",
            "format": "int32"
        }
        attributes = {}
        if resource.schema:
            attributes = {
                '$ref': f'#/definitions/{create_schema_name(resource.schema)}'
            }
        schema = default_schema if default_schema else {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'object',
                    'properties': {
                        'type': {
                            'type': 'string'
                        },
                        'id': {
                            'type': 'string'
                        },
                        'attributes': attributes,
                        'relationships': {
                            'type': 'object'
                        }
                    },
                    'required': [
                        'type'
                    ]
                }
            }
        }

        if 'get' in methods:
            operations['get'] = deepcopy(operations_all)
            operations['get']['responses'] = {
                '200': {'description': 'Success'},
                '404': {'description': 'Not Found'},
            }
            # Если выгружаем объект
            if issubclass(resource, ResourceDetail):
                operations['get']['parameters'].append(deepcopy(parameter_id))
            models_for_include = ','.join([
                    i_field_name
                    for i_field_name, i_field in resource.schema._declared_fields.items()
                    if isinstance(i_field, Relationship)
                ])
            operations['get']['parameters'].append({
                'default': models_for_include,
                'name': 'include',
                'in': 'query',
                'format': 'string',
                'required': False,
                'description': f'Related relationships to include. For example: {models_for_include}'
            })

            # Sparse Fieldsets
            description = 'List that refers to the name(s) of the fields to be returned "%s"'
            new_parameter = {
                'name': f'fields[{resource.schema.Meta.type_}]',
                'in': 'query',
                'type': 'array',
                'required': False,
                'description': description.format(resource.schema.Meta.type_),
                'items': {
                    'type': 'string',
                    'enum': list(resource.schema._declared_fields.keys())
                }
            }
            operations['get']['parameters'].append(new_parameter)
            type_schemas = {resource.schema.Meta.type_}
            for i_field_name, i_field in resource.schema._declared_fields.items():
                if isinstance(i_field, Relationship) and i_field.schema.Meta.type_ not in type_schemas:
                    new_parameter = {
                        'name': f'fields[{i_field.schema.Meta.type_}]',
                        'in': 'query',
                        'type': 'array',
                        'required': False,
                        'description': description.format(i_field.schema.Meta.type_),
                        'items': {
                            'type': 'string',
                            'enum': list(self.spec.components._schemas[create_schema_name(schema=i_field.schema)]['properties'].keys())
                        }
                    }
                    operations['get']['parameters'].append(new_parameter)
                    type_schemas.add(i_field.schema.Meta.type_)

            # Filter
            if issubclass(resource, ResourceList):
                # List data
                operations['get']['parameters'].append({
                    'default': 1,
                    'name': 'page[number]',
                    'in': 'query',
                    'format': 'int64',
                    'required': False,
                    'description': 'Page offset'
                })
                operations['get']['parameters'].append({
                    'default': 10,
                    'name': 'page[size]',
                    'in': 'query',
                    'format': 'int64',
                    'required': False,
                    'description': 'Max number of items'
                })
                operations['get']['parameters'].append({
                    'name': 'sort',
                    'in': 'query',
                    'format': 'string',
                    'required': False,
                    'description': 'Sort'
                })
                operations['get']['parameters'].append({
                    'name': 'filter',
                    'in': 'query',
                    'format': 'string',
                    'required': False,
                    'description': 'Filter (https://flask-rest-jsonapi.readthedocs.io/en/latest/filtering.html)'
                })
                # Add filters for fields
                for i_field_name, i_field in resource.schema._declared_fields.items():
                    i_field_spec = self.spec.components._schemas[create_schema_name(schema=resource.schema)]['properties'][i_field_name]
                    if not isinstance(i_field, fields.Nested):
                        if i_field_spec.get('type') == 'object':
                            # Пропускаем создание фильтров для dict. Просто не понятно как фильтровать по таким
                            # полям
                            continue
                        new_parameter = {
                            'name': f'filter[{i_field_name}]',
                            'in': 'query',
                            'type': i_field_spec.get('type'),
                            'required': False,
                            'description': f'{i_field_name} attribute filter'
                        }
                        if 'items' in i_field_spec:
                            new_items = {
                                'type': i_field_spec['items'].get('type'),
                            }
                            if 'enum' in i_field_spec['items']:
                                new_items['enum'] = i_field_spec['items']['enum']
                            new_parameter.update({'items': new_items})
                        operations['get']['parameters'].append(new_parameter)
                    elif isinstance(i_field, fields.Nested) and \
                            getattr(getattr(i_field.schema, 'Meta', object), 'filtering', False):
                        # Делаем возможность фильтровать JSONB
                        for i_field_jsonb_name, i_field_jsonb in i_field.schema._declared_fields.items():
                            i_field_jsonb_spec = self.spec.components._schemas[create_schema_name(schema=i_field.schema)]['properties'][i_field_jsonb_name]
                            if i_field_jsonb_spec.get('type') == 'object':
                                # Пропускаем создание фильтров для dict. Просто не понятно как фильтровать по таким
                                # полям
                                continue
                            new_parameter = {
                                'name': f'filter[{i_field_name}__{i_field_jsonb_name}]',
                                'in': 'query',
                                'type': i_field_jsonb_spec.get('type'),
                                'required': False,
                                'description': f'{i_field_name}__{i_field_jsonb_name} attribute filter'
                            }
                            if 'items' in i_field_jsonb_spec:
                                new_items = {
                                    'type': i_field_jsonb_spec['items'].get('type'),
                                }
                                if 'enum' in i_field_jsonb_spec['items']:
                                    new_items['enum'] = i_field_jsonb_spec['items']['enum']
                                new_parameter.update({'items': new_items})
                            operations['get']['parameters'].append(new_parameter)

        if 'post' in methods:
            operations['post'] = deepcopy(operations_all)
            operations['post']['responses'] = {
                '201': {'description': 'Created'},
                '202': {'description': 'Accepted'},
                '403': {'description': 'This implementation does not accept client-generated IDs'},
                '404': {'description': 'Not Found'},
                '409': {'description': 'Conflict'}
            }
            operations['post']['parameters'].append({
                'name': 'POST body',
                'in': 'body',
                'schema': schema,
                'required': True,
                'description': f'{tag_name} attributes'
            })
        if 'patch' in methods:
            operations['patch'] = deepcopy(operations_all)
            operations['patch']['responses'] = {
                '200': {'description': 'Success'},
                '201': {'description': 'Created'},
                '204': {'description': 'No Content'},
                '403': {'description': 'Forbidden'},
                '404': {'description': 'Not Found'},
                '409': {'description': 'Conflict'}
            }
            operations['patch']['parameters'].append(deepcopy(parameter_id))
            operations['patch']['parameters'].append({
                'name': 'POST body',
                'in': 'body',
                'schema': schema,
                'required': True,
                'description': f'{tag_name} attributes'
            })
        if 'delete' in methods:
            operations['delete'] = deepcopy(operations_all)
            operations['delete']['parameters'].append(deepcopy(parameter_id))
            operations['delete']['responses'] = {
                '200': {'description': 'Success'},
                '202': {'description': 'Accepted'},
                '204': {'description': 'No Content'},
                '403': {'description': 'Forbidden'},
                '404': {'description': 'Not Found'}
            }
        rule = None
        for i_rule in self.app.url_map._rules:
            if i_rule.rule == path:
                rule = i_rule
                break
        if APISPEC_VERSION_MAJOR < 1:
            self.spec.add_path(path=path, operations=operations, rule=rule, resource=resource, **kwargs)
        else:
            self.spec.path(path=path, operations=operations, rule=rule, resource=resource, **kwargs)

    def _add_definitions_in_spec(self, schema) -> None:
        """
        Add schema in spec
        :param schema: schema marshmallow
        :return:
        """
        name_schema = create_schema_name(schema)
        if name_schema not in self.spec_schemas and name_schema not in self.spec.components._schemas:
            self.spec_schemas[name_schema] = schema
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(name_schema, schema=schema)
            else:
                self.spec.components.schema(name_schema, schema=schema)

    def _add_tags_in_spec(self, tag: Dict[str, str]) -> None:
        """
        Add tags in spec
        :param tag: {'name': '<name tag>', 'description': '<tag description>', 'add_in_spec': <added tag in spec?>}
        :return:
        """
        if tag.get('add_in_spec', True) is False:
            self.spec_tag[tag['name']]['add_in_spec'] = True
            tag_in_spec = {'name': tag['name'], 'description': tag['description']}
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.add_tag(tag_in_spec)
            else:
                self.spec.tag(tag_in_spec)


# Рефактор, чтобы не выкидывались варнинги о том что схема уже добавлена, переделал формирования имени для существующих
# схем
def resolve_nested_schema(self, schema):
    """Return the Open API representation of a marshmallow Schema.

    Adds the schema to the spec if it isn't already present.

    Typically will return a dictionary with the reference to the schema's
    path in the spec unless the `schema_name_resolver` returns `None`, in
    which case the returned dictoinary will contain a JSON Schema Object
    representation of the schema.

    :param schema: schema to add to the spec
    """
    schema_instance = resolve_schema_instance(schema)
    schema_key = make_schema_key(schema_instance)
    if schema_key not in self.refs:
        schema_cls = self.resolve_schema_class(schema)
        name = self.schema_name_resolver(schema_cls)
        if not name:
            try:
                json_schema = self.schema2jsonschema(schema)
            except RuntimeError:
                raise APISpecError(
                    "Name resolver returned None for schema {schema} which is "
                    "part of a chain of circular referencing schemas. Please"
                    " ensure that the schema_name_resolver passed to"
                    " MarshmallowPlugin returns a string for all circular"
                    " referencing schemas.".format(schema=schema)
                )
            if getattr(schema, "many", False):
                return {"type": "array", "items": json_schema}
            return json_schema
        name = create_schema_name(schema=schema_instance)
        if name not in self.spec.components._schemas:
            self.spec.components.schema(name, schema=schema)
    return self.get_ref_dict(schema_instance)


OpenAPIConverter.resolve_nested_schema = resolve_nested_schema
