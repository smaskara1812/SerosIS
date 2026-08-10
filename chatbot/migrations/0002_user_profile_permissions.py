from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("user_login_id", models.CharField(max_length=20, primary_key=True, serialize=False)),
                ("is_app_admin",  models.BooleanField(default=False)),
                ("created_at",    models.DateTimeField(auto_now_add=True)),
                ("updated_at",    models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "cb_user_profile"},
        ),
        migrations.CreateModel(
            name="UserPermission",
            fields=[
                ("id",            models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("user_login_id", models.CharField(db_index=True, max_length=20)),
                ("menu_key",      models.CharField(max_length=60)),
                ("can_view",      models.BooleanField(default=False)),
                ("can_add",       models.BooleanField(default=False)),
                ("can_edit",      models.BooleanField(default=False)),
                ("can_delete",    models.BooleanField(default=False)),
                ("can_export",    models.BooleanField(default=False)),
                ("granted_by",    models.CharField(blank=True, max_length=20)),
                ("granted_at",    models.DateTimeField(auto_now_add=True)),
                ("updated_at",    models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "cb_user_permissions",
                "unique_together": {("user_login_id", "menu_key")},
            },
        ),
    ]
