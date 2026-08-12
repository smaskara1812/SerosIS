from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0005_user_id_key"),
    ]

    operations = [
        migrations.CreateModel(
            name="CbMstUserPassword",
            fields=[
                ("user_id",       models.IntegerField(primary_key=True, serialize=False)),
                ("password_hash", models.CharField(max_length=64)),
                ("set_at",        models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "cb_mst_user_password"},
        ),
    ]
