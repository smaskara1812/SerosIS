from django.db import migrations


class Migration(migrations.Migration):
    """
    Historically this migration transitioned cb_user_profile/cb_user_permissions
    from a user_login_id (string) key to user_id (integer from Mst_user). That
    schema is now created directly by 0002 (migration 0002 was rewritten to
    define user_id from the start), so nothing further is needed here for a
    fresh install. Kept as a placeholder (empty operations) purely so the
    migration dependency chain and history stay intact for databases that
    already applied this migration under its old (pre-rewrite) content —
    Django tracks applied migrations by name only, not by content, so this is
    safe to have changed retroactively.
    """

    dependencies = [
        ("chatbot", "0004_cb_menu_group_order"),
    ]

    operations = []
