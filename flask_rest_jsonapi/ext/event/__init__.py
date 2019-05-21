import urllib.parse

from marshmallow import Schema, fields
from marshmallow.class_registry import register

from flask_rest_jsonapi.exceptions import PluginMethodNotImplementedError
from flask_rest_jsonapi.plugin import BasePlugin


class EventSchema(Schema):
    pass


class EventPlugin(BasePlugin):
    """Плагин для создания роутеров на события в json_api"""

    def before_route(self, resource=None, view=None, urls=None, self_json_api=None, **kwargs):

        if hasattr(resource, 'events'):
            # Создание роутеров для событий (events)
            cls_events = getattr(resource, 'events', object)
            events = [getattr(cls_events, i_event) for i_event in dir(cls_events) if i_event.startswith('event_')]
            for i_event in events:
                i_resource = type(i_event.__name__, (resource,), {
                    'methods': ['POST'],
                    'schema': None,
                    'post': i_event
                })
                i_view = f'{view}_{i_event.__name__}'

                url_rule_options = kwargs.get('url_rule_options') or dict()

                i_urls = [urllib.parse.urljoin(i_url, i_event.__name__) for i_url in urls]
                i_resource.decorators = self_json_api.decorators

                view_func = i_resource.as_view(i_view)

                if self_json_api.blueprint is not None:
                    i_resource.view = '.'.join([self_json_api.blueprint.name, i_resource.view])
                    for url in i_urls:
                        self_json_api.blueprint.add_url_rule(url, view_func=view_func, **url_rule_options)
                elif self_json_api.app is not None:
                    for url in i_urls:
                        self_json_api.app.add_url_rule(url, view_func=view_func, **url_rule_options)
                else:
                    self_json_api.resources.append({'resource': i_resource,
                                                    'view': i_view,
                                                    'urls': i_urls,
                                                    'url_rule_options': url_rule_options})

                for i_plugins in self_json_api.plugins:
                    try:
                        i_plugins.after_route(view=view,
                                              urls=tuple(i_urls),
                                              self_json_api=self_json_api,
                                              default_schema=None,
                                              resource=i_resource,
                                              **kwargs)
                    except PluginMethodNotImplementedError:
                        pass
