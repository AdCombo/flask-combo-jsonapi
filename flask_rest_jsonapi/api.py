# -*- coding: utf-8 -*-

"""This module contains the main class of the Api to initialize the Api, plug default decorators for each resources
methods, speficy which blueprint to use, define the Api routes and plug additional oauth manager and permission manager
"""

import inspect
from copy import deepcopy
from functools import wraps

from flask import request, abort

from typing import Dict, Any, Set

from marshmallow import Schema, fields

from flask_rest_jsonapi.marshmallow_fields import Relationship
from flask_rest_jsonapi.spec import APISpec, DocBlueprintMixin
from flask_rest_jsonapi.compat import APISPEC_VERSION_MAJOR

from flask_rest_jsonapi.resource import ResourceList, ResourceRelationship
from flask_rest_jsonapi.decorators import jsonapi_exception_formatter


class Api(DocBlueprintMixin):
    """The main class of the Api"""

    def __init__(self, app=None, blueprint=None, decorators=None, decorators_for_autodoc=None, spec_kwargs=None):
        """Initialize an instance of the Api

        :param app: the flask application
        :param blueprint: a flask blueprint
        :param tuple decorators: a tuple of decorators plugged to each resource methods
        :param tuple decorators_for_autodoc:
        :param dict spec_kwargs:
        """
        self.app = app
        self._app = app
        self.blueprint = blueprint
        self.resources = []
        self.resource_registry = []
        self.decorators = decorators or tuple()
        self.decorators_for_autodoc = decorators_for_autodoc or tuple()
        self.spec = None
        self.spec_tag = {}
        self.spec_schemas = {}
        # Use lists to enforce order
        self._definitions = []
        self._fields = []
        self._converters = []

        if app is not None:
            self.init_app(app, blueprint, spec_kwargs=spec_kwargs)

    def init_app(self, app=None, blueprint=None, additional_blueprints=None, spec_kwargs=None):
        """Update flask application with our api

        :param Application app: a flask application
        """

        self._app = app
        if app is not None:
            self.app = app

        if blueprint is not None:
            self.blueprint = blueprint

        for resource in self.resources:
            self.route(resource['resource'],
                       resource['view'],
                       *resource['urls'],
                       url_rule_options=resource['url_rule_options'])

        if self.blueprint is not None:
            self.app.register_blueprint(self.blueprint)

        if additional_blueprints is not None:
            for blueprint in additional_blueprints:
                self.app.register_blueprint(blueprint)

        self.app.config.setdefault('PAGE_SIZE', 30)

        # Initialize spec
        spec_kwargs = spec_kwargs or {}
        openapi_version = app.config.get('OPENAPI_VERSION', '2.0')
        openapi_major_version = int(openapi_version.split('.')[0])
        if openapi_major_version < 3:
            base_path = app.config.get('APPLICATION_ROOT')
            # Don't pass basePath if '/' to avoid a bug in apispec
            # https://github.com/marshmallow-code/apispec/issues/78#issuecomment-431854606
            # TODO: Remove this condition when the bug is fixed
            if base_path != '/':
                spec_kwargs.setdefault('basePath', base_path)
        spec_kwargs.update(app.config.get('API_SPEC_OPTIONS', {}))
        self.spec = APISpec(
            app.name,
            app.config.get('API_VERSION', '1'),
            openapi_version=openapi_version,
            **spec_kwargs,
        )
        # Register custom fields in spec
        for args in self._fields:
            self.spec.register_field(*args)
        # Register schema definitions in spec
        for name, schema_cls, kwargs in self._definitions:
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(name, schema=schema_cls, **kwargs)
            else:
                self.spec.components.schema(name, schema=schema_cls, **kwargs)
        # Register custom converters in spec
        for args in self._converters:
            self.spec.register_converter(*args)

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

    def route(self, resource, view, *urls, **kwargs):
        """Create an api view.

        :param Resource resource: a resource class inherited from flask_rest_jsonapi.resource.Resource
        :param str view: the view name
        :param list urls: the urls of the view
        :param dict kwargs: additional options of the route
        """
        resource.view = view
        url_rule_options = kwargs.get('url_rule_options') or dict()

        view_func = resource.as_view(view)

        if 'blueprint' in kwargs:
            resource.view = '.'.join([kwargs['blueprint'].name, resource.view])
            for url in urls:
                kwargs['blueprint'].add_url_rule(url, view_func=view_func, **url_rule_options)
        elif self.blueprint is not None:
            resource.view = '.'.join([self.blueprint.name, resource.view])
            for url in urls:
                self.blueprint.add_url_rule(url, view_func=view_func, **url_rule_options)
        elif self.app is not None:
            for url in urls:
                self.app.add_url_rule(url, view_func=view_func, **url_rule_options)
        else:
            self.resources.append({'resource': resource,
                                   'view': view,
                                   'urls': urls,
                                   'url_rule_options': url_rule_options})

        # self.resource_registry.append(resource)

        # Register views in API documentation for this resource
        # resource.register_views_in_doc(self._app, self.spec)
        # Add tag relative to this resource to the global tag list

        # We add definitions (models) to the apiscpec
        self._add_definitions_in_spec(resource.schema)

        # We add tags to the apiscpec
        tag_name = view.title()
        if 'tag' not in kwargs and view.title() not in self.spec_tag:
            tag = {'name': view.title(), 'description': '', 'add_in_spec': False}
            self.spec_tag[tag['name']] = tag
            self._add_tags_in_spec(tag)
        else:
            tag_name = self.spec_tag[kwargs['tag']]['name']

        self._add_paths_in_spec(path=url, resource=resource, tag_name=tag_name)

    def _add_paths_in_spec(self, path: str, resource: Any, tag_name: str = '') -> None:
        operations = {}
        methods: Set[str] = {i_method.lower() for i_method in resource.methods}
        operations_all: Dict[str, Any] = {
            'tags': [tag_name],
            'produces': [
                'application/json'
            ],
            'parameters': []
        }

        schema = {
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
                        'attributes': {
                            '$ref': f'#/definitions/{resource.schema.__name__}'
                        },
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
            operations['get']['parameters'].append({
                'default': ','.join([
                    i_field_name
                    for i_field_name, i_field in resource.schema._declared_fields.items()
                    if isinstance(i_field, Relationship)
                ]),
                'name': 'include',
                'in': 'query',
                'format': 'string',
                'required': False,
                'description': 'Related relationships to include'
            })
            if not (methods - {'get', 'post'}):
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
                    operations['get']['parameters'].append({
                        'type': 'string',
                        'name': f'filter[{i_field_name}]',
                        'in': 'query',
                        'format': 'string',
                        'required': False,
                        'description': f'{i_field_name} attribute filter'
                    })
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
            operations['patch']['parameters'].append({
                'name': 'POST body',
                'in': 'body',
                'schema': schema,
                'required': True,
                'description': f'{tag_name} attributes'
            })
        if 'delete' in methods:
            operations['delete'] = deepcopy(operations_all)
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
            self.spec.add_path(path=path, operations=operations, rule=rule)
        else:
            self.spec.path(path=path, operations=operations, rule=rule)

    def _add_definitions_in_spec(self, schema) -> None:
        """
        Add schema in spec
        :param schema: schema marshmallow
        :return:
        """
        name_schema = schema.__name__
        if name_schema not in self.spec_schemas and name_schema not in self.spec.components._schemas:
            self.spec_schemas[name_schema] = schema
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(name_schema, schema=schema)
            else:
                self.spec.components.schema(name_schema, schema=schema)

    def add_tags_in_doc(self, tags: Dict[str, str]) -> None:
        """
        Add list of tags and description of them
        :param tags: {'<name tag>': '<description tag>'}
        :return:
        """
        for tag_name, tag_description in tags.items():
            self.spec_tag[tag_name] = {'name': tag_name, 'description': tag_description, 'add_in_spec': False}
            self._add_tags_in_spec(self.spec_tag[tag_name])

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

    def oauth_manager(self, oauth_manager):
        """Use the oauth manager to enable oauth for API

        :param oauth_manager: the oauth manager
        """
        @self.app.before_request
        def before_request():
            endpoint = request.endpoint
            resource = None
            if endpoint:
                resource = getattr(self.app.view_functions[endpoint], 'view_class', None)

            if resource and not getattr(resource, 'disable_oauth', None):
                scopes = request.args.get('scopes')

                if getattr(resource, 'schema'):
                    scopes = [self.build_scope(resource, request.method)]
                elif scopes:
                    scopes = scopes.split(',')

                    if scopes:
                        scopes = scopes.split(',')

                valid, req = oauth_manager.verify_request(scopes)

                for func in oauth_manager._after_request_funcs:
                    valid, req = func(valid, req)

                if not valid:
                    if oauth_manager._invalid_response:
                        return oauth_manager._invalid_response(req)
                    return abort(401)

                request.oauth = req

    @staticmethod
    def build_scope(resource, method):
        """Compute the name of the scope for oauth

        :param Resource resource: the resource manager
        :param str method: an http method
        :return str: the name of the scope
        """
        if ResourceList in inspect.getmro(resource) and method == 'GET':
            prefix = 'list'
        else:
            method_to_prefix = {'GET': 'get',
                                'POST': 'create',
                                'PATCH': 'update',
                                'DELETE': 'delete'}
            prefix = method_to_prefix[method]

            if ResourceRelationship in inspect.getmro(resource):
                prefix = '_'.join([prefix, 'relationship'])

        return '_'.join([prefix, resource.schema.opts.type_])

    def permission_manager(self, permission_manager, with_decorators=True):
        """Use permission manager to enable permission for API

        :param callable permission_manager: the permission manager
        """
        self.check_permissions = permission_manager

        if with_decorators:
            for resource in self.resource_registry:
                if getattr(resource, 'disable_permission', None) is not True:
                    for method in getattr(resource, 'methods', ('GET', 'POST', 'PATCH', 'DELETE')):
                        setattr(resource,
                                method.lower(),
                                self.has_permission()(getattr(resource, method.lower())))

    def has_permission(self, *args, **kwargs):
        """Decorator used to check permissions before to call resource manager method"""
        def wrapper(view):
            if getattr(view, '_has_permissions_decorator', False) is True:
                return view

            @wraps(view)
            @jsonapi_exception_formatter
            def decorated(*view_args, **view_kwargs):
                self.check_permissions(view, view_args, view_kwargs, *args, **kwargs)
                return view(*view_args, **view_kwargs)
            decorated._has_permissions_decorator = True
            return decorated
        return wrapper

    @staticmethod
    def check_permissions(view, view_args, view_kwargs, *args, **kwargs):
        """The function use to check permissions

        :param callable view: the view
        :param list view_args: view args
        :param dict view_kwargs: view kwargs
        :param list args: decorator args
        :param dict kwargs: decorator kwargs
        """
        raise NotImplementedError
