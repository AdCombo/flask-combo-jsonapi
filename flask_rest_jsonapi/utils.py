import simplejson as json
from uuid import UUID
from datetime import datetime


"""
Splitter for filters, sorts and includes
Previously used: '__'
"""
SPLIT_REL = '.'


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
