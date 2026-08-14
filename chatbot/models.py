import uuid
from django.db import models


class UserProfile(models.Model):
    user_id       = models.IntegerField(primary_key=True)   # USER_ID from Mst_user
    user_login_id = models.CharField(max_length=20, db_index=True)  # for session lookup
    is_app_admin  = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_user_profile"

    def __str__(self):
        return self.user_login_id


class UserPermission(models.Model):
    user_id    = models.IntegerField(db_index=True)   # USER_ID from Mst_user
    menu_key   = models.CharField(max_length=60)
    can_view   = models.BooleanField(default=False)
    can_add    = models.BooleanField(default=False)
    can_edit   = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    granted_by = models.CharField(max_length=20, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_user_permissions"
        unique_together = [("user_id", "menu_key")]

    def __str__(self):
        return f"{self.user_id}:{self.menu_key}"


class CbMenu(models.Model):
    menu_key         = models.CharField(max_length=60, unique=True)
    menu_label       = models.CharField(max_length=60)
    menu_group       = models.CharField(max_length=40, blank=True)
    group_order      = models.SmallIntegerField(default=0)
    menu_order       = models.SmallIntegerField(default=0)
    view_available   = models.BooleanField(default=True)
    add_available    = models.BooleanField(default=False)
    edit_available   = models.BooleanField(default=False)
    delete_available = models.BooleanField(default=False)
    export_available = models.BooleanField(default=False)
    upload_available = models.BooleanField(default=False)
    is_active        = models.BooleanField(default=True)
    cr_dt            = models.DateTimeField(auto_now_add=True)
    mod_dt           = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_menu"
        ordering = ["group_order", "menu_order"]

    def __str__(self):
        return f"{self.menu_key} ({self.menu_label})"

    def get_actions(self):
        actions = []
        if self.view_available:   actions.append("view")
        if self.add_available:    actions.append("add")
        if self.edit_available:   actions.append("edit")
        if self.delete_available: actions.append("delete")
        if self.export_available: actions.append("export")
        if self.upload_available: actions.append("upload")
        return actions


class CbMstUserPassword(models.Model):
    user_id       = models.IntegerField(primary_key=True)
    password_hash = models.CharField(max_length=64)  # SHA-256 hex
    set_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_mst_user_password"

    def __str__(self):
        return f"LocalPwd(user_id={self.user_id})"


class CbAuditLog(models.Model):
    """Append-only audit trail of actions performed in the system.
    Lives in the chathistory DB (cb_ prefix routes it there). Never edited/deleted from the app."""
    ts           = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id      = models.IntegerField(null=True, blank=True, db_index=True)  # Mst_user USER_ID; null for superuser w/o profile
    username     = models.CharField(max_length=50)                            # login id, e.g. "smaskara"
    action       = models.CharField(max_length=24, db_index=True)            # create/update/delete/deactivate/export/login/login_failed/logout/permission_change
    entity       = models.CharField(max_length=60, db_index=True)            # e.g. "masters.hazard_types", "auth", "admin.user_rights"
    entity_label = models.CharField(max_length=80, blank=True)               # human label, e.g. "Hazard Type"
    record_id    = models.CharField(max_length=40, blank=True)               # affected row PK (string; blank if N/A)
    record_label = models.CharField(max_length=200, blank=True)              # affected row's name
    changes      = models.JSONField(null=True, blank=True)                   # {column: {"old": ..., "new": ...}}
    ip           = models.CharField(max_length=45, blank=True)
    user_agent   = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "cb_audit_log"
        ordering = ["-ts"]
        indexes = [
            models.Index(fields=["entity", "ts"]),
            models.Index(fields=["user_id", "ts"]),
            models.Index(fields=["action", "ts"]),
        ]

    def __str__(self):
        return f"{self.ts} {self.username} {self.action} {self.entity}"


class Conversation(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title      = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_conversations"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    ROLE_USER      = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES   = [(ROLE_USER, "User"), (ROLE_ASSISTANT, "Assistant")]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content      = models.TextField()
    sources      = models.JSONField(default=list, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cb_messages"
        ordering = ["created_at"]
