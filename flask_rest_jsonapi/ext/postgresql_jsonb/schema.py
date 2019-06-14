from marshmallow import Schema


class SchemaJSONB(Schema):
    class Meta:
        # Есть ли фильтрация по данной схеме.
        filtering = True
