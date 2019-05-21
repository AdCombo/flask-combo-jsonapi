from marshmallow import Schema


class SchemaJOSNB(Schema):
    class Meta:
        # Есть ли фильтрация по данной схеме.
        filtering = True
