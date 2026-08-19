from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Switch permission tables from user_login_id (string) to user_id (integer
    from Mst_user) as the primary / foreign key.

    This migration handles the state after two failed partial runs (MySQL DDL
    is non-transactional, so prior runs partially applied changes).

    Current actual DB state when this migration runs:
      cb_user_profile     — ALREADY CORRECT (user_id INT PK, user_login_id INDEX)
      cb_user_permissions — user_id INT column exists, user_login_id removed,
                            but no unique constraint yet and 80 stale rows (all user_id=0)
    """

    dependencies = [
        ("chatbot", "0004_cb_menu_group_order"),
    ]

    operations = [
        # ── cb_user_profile: already correct in DB, just sync Django state ────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # No-op: table is already in the right shape from prior partial runs.
                migrations.RunSQL(sql="SELECT 1", reverse_sql="SELECT 1"),
            ],
            state_operations=[
                migrations.RemoveField(model_name="userprofile", name="user_login_id"),
                migrations.AddField(
                    model_name="userprofile",
                    name="user_id",
                    field=models.IntegerField(primary_key=True, serialize=False),
                ),
                migrations.AddField(
                    model_name="userprofile",
                    name="user_login_id",
                    field=models.CharField(max_length=20, db_index=True, default=""),
                    preserve_default=False,
                ),
            ],
        ),

        # ── cb_user_permissions: user_id column exists but needs cleanup ───────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Standalone CREATE/DROP INDEX statements (not ALTER TABLE ... ADD
                # INDEX, which is MySQL-only syntax) so this runs unchanged on both
                # MySQL and SQL Server.
                migrations.RunSQL(
                    sql=[
                        # Rows are stale (user_id=0 for all). Safe to clear in dev.
                        "TRUNCATE TABLE cb_user_permissions;",
                        "CREATE UNIQUE INDEX cb_user_perms_uid_menu_uniq ON cb_user_permissions (user_id, menu_key);",
                        "CREATE INDEX cb_user_perms_uid_idx ON cb_user_permissions (user_id);",
                    ],
                    reverse_sql=[
                        "TRUNCATE TABLE cb_user_permissions;",
                        "DROP INDEX cb_user_perms_uid_menu_uniq ON cb_user_permissions;",
                        "DROP INDEX cb_user_perms_uid_idx ON cb_user_permissions;",
                        "ALTER TABLE cb_user_permissions ADD user_login_id VARCHAR(20) NOT NULL DEFAULT '';",
                        "CREATE INDEX cb_user_perms_login_idx ON cb_user_permissions (user_login_id);",
                        "CREATE UNIQUE INDEX cb_user_perms_login_menu_uniq ON cb_user_permissions (user_login_id, menu_key);",
                        "ALTER TABLE cb_user_permissions DROP COLUMN user_id;",
                    ],
                ),
            ],
            state_operations=[
                # Tell Django the old string unique_together is gone
                migrations.AlterUniqueTogether(
                    name="userpermission",
                    unique_together=set(),
                ),
                # Remove the old string column from Django state
                migrations.RemoveField(
                    model_name="userpermission",
                    name="user_login_id",
                ),
                # Add the integer column to Django state
                migrations.AddField(
                    model_name="userpermission",
                    name="user_id",
                    field=models.IntegerField(db_index=True, default=0),
                    preserve_default=False,
                ),
                # Register the new unique_together in Django state
                migrations.AlterUniqueTogether(
                    name="userpermission",
                    unique_together={("user_id", "menu_key")},
                ),
            ],
        ),
    ]
