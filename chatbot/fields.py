import json

from django.db import models


class PortableJSONField(models.TextField):
    """JSON field that works on both MySQL and SQL Server.

    mssql-django's backend does not support Django's built-in JSONField
    (fields.E180: "SQL Server does not support JSONFields"). This stores the
    value as text and transparently serializes/deserializes it, so calling
    code keeps reading and writing normal Python objects (dicts/lists) exactly
    as it would with JSONField — only the migration/column type differs.
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def to_python(self, value):
        if value is None or not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)
