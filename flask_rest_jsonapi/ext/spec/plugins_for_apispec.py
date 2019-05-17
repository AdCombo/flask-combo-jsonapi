import re

from apispec import BasePlugin

from apispec.yaml_utils import load_yaml_from_docstring

RE_URL = re.compile(r'<(?:[^:<>]+:)?([^<>]+)>')


def flaskpath2swagger(path):
    """Convert a Flask URL rule to an OpenAPI-compliant path.

    :param str path: Flask path template.
    """
    return RE_URL.sub(r'{\1}', path)


class RestfulPlugin(BasePlugin):
    def init_spec(self, spec):
        super().init_spec(spec)
        self.spec = spec

    def operation_helper(self, path=None, operations=None, **kwargs):
        """Если для query параметров указали схему marshmallow, то раскрываем её и вытаскиваем параметры первого уровня,
            без Nested"""
        resource = kwargs.get('resource', None)
        for m in getattr(resource, 'methods', []):
            m = m.lower()
            f = getattr(resource, m)
            m_ops = load_yaml_from_docstring(f.__doc__)
            if m_ops:
                operations.update({m: m_ops})
        for method, val in operations.items():
            for index, parametr in enumerate(val['parameters'] if 'parameters' in val else []):
                if 'in' in parametr and parametr['in'] == 'query' and 'schema' in parametr:
                    name_schema = parametr['schema']['$ref'].split('/')[-1]
                    new_parameters = []
                    if name_schema in self.spec.components._schemas:
                        for i_name, i_value in self.spec.components._schemas[name_schema]['properties'].items():
                            new_parameter = {
                                'name': i_name,
                                'in': 'query',
                                'type': i_value.get('type'),
                                'description': i_value.get('description', '')
                            }
                            if 'items' in i_value:
                                new_items = {
                                    'type': i_value['items'].get('type'),
                                }
                                if 'enum' in i_value['items']:
                                    new_items['enum'] = i_value['items']['enum']
                                new_parameter.update({'items': new_items})
                            new_parameters.append(new_parameter)
                    del val['parameters'][index]
                    val['parameters'].extend(new_parameters)

    def path_helper(self, path=None, operations=None, urls=None, resource=None, **kwargs):
        """Path helper that allows passing a Flask view function."""
        path = flaskpath2swagger(urls[0]) if urls else flaskpath2swagger(path)
        return path
