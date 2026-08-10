import uuid
from django.db import models


class UserProfile(models.Model):
    user_login_id = models.CharField(max_length=20, primary_key=True)
    is_app_admin  = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_user_profile"

    def __str__(self):
        return self.user_login_id


class UserPermission(models.Model):
    user_login_id = models.CharField(max_length=20, db_index=True)
    menu_key      = models.CharField(max_length=60)
    can_view      = models.BooleanField(default=False)
    can_add       = models.BooleanField(default=False)
    can_edit      = models.BooleanField(default=False)
    can_delete    = models.BooleanField(default=False)
    can_export    = models.BooleanField(default=False)
    granted_by    = models.CharField(max_length=20, blank=True)
    granted_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cb_user_permissions"
        unique_together = [("user_login_id", "menu_key")]

    def __str__(self):
        return f"{self.user_login_id}:{self.menu_key}"


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
