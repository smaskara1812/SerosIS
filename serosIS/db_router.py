# Routes:
#   auth / contenttypes / sessions  → chathistory (Django's own system tables)
#   chatbot app (all cb_* tables)   → chathistory
#   everything else                 → default (read-only ops DB, no migrations)

_CHATHISTORY_APPS = frozenset({"admin", "auth", "contenttypes", "sessions", "chatbot"})


class ChatHistoryRouter:
    def _use_chathistory(self, model):
        return (
            model._meta.app_label in _CHATHISTORY_APPS
            or model._meta.db_table.startswith("cb_")
        )

    def db_for_read(self, model, **hints):
        return "chathistory" if self._use_chathistory(model) else None

    def db_for_write(self, model, **hints):
        return "chathistory" if self._use_chathistory(model) else None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in _CHATHISTORY_APPS:
            return db == "chathistory"
        if db == "chathistory":
            return False
        if db == "default":
            return False
        return None
