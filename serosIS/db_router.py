# All chatbot history models have cb_-prefixed table names.
# This router sends them to the "chathistory" database and keeps
# everything else on "default".

_CHAT_MODELS = frozenset({"conversation", "message"})
_CHAT_APP = "chatbot"


class ChatHistoryRouter:
    def db_for_read(self, model, **hints):
        if model._meta.db_table.startswith("cb_"):
            return "chathistory"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.db_table.startswith("cb_"):
            return "chathistory"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in _CHAT_MODELS and app_label == _CHAT_APP:
            return db == "chathistory"
        # Block ALL migrations on chathistory (non-chat models don't belong there)
        if db == "chathistory":
            return False
        # Block ALL migrations on default — it is the read-only operational DB.
        # Django should never create tables there.
        if db == "default":
            return False
        return None
