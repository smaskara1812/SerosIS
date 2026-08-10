from django.db import migrations, models


SEED_ROWS = [
    # (menu_key, menu_label, menu_group, menu_order, view, add, edit, delete, export, upload)
    ("dashboard",               "Dashboard (main)",  "Overview",  1,  True,  False, False, False, False, False),
    ("dashboard.operations",    "Operations",        "Overview",  2,  True,  False, False, False, False, False),
    ("dashboard.hse",           "HSE / Safety",      "Overview",  3,  True,  False, False, False, False, False),
    ("dashboard.workforce",     "Workforce",         "Overview",  4,  True,  False, False, False, False, False),
    ("dashboard.finance",       "Finance",           "Overview",  5,  True,  False, False, False, False, False),
    ("rigs",                    "Rigs 360",          "Overview",  6,  True,  False, False, False, False, False),
    ("listings.incidents",      "Incidents",         "Listings",  10, True,  False, False, False, True,  False),
    ("listings.hazard_cards",   "Hazard Cards",      "Listings",  11, True,  False, False, False, True,  False),
    ("listings.employees",      "Employees",         "Listings",  12, True,  False, False, False, True,  False),
    ("listings.staff",          "Staff",             "Listings",  13, True,  False, False, False, True,  False),
    ("listings.crew_rotations", "Crew Rotations",    "Listings",  14, True,  False, False, False, True,  False),
    ("listings.invoices",       "Invoices",          "Listings",  15, True,  False, False, False, True,  False),
    ("listings.certificates",   "Certificates",      "Listings",  16, True,  False, False, False, True,  False),
    ("listings.users",          "System Users",      "Listings",  17, True,  False, False, False, False, False),
    ("masters.rigs",            "Rigs",              "Masters",   20, True,  True,  True,  True,  False, False),
    ("masters.operators",       "Operators",         "Masters",   21, True,  True,  True,  True,  False, False),
    ("masters.contractors",     "Contractors",       "Masters",   22, True,  True,  True,  True,  False, False),
    ("masters.cost_centres",    "Cost Centres",      "Masters",   23, True,  True,  True,  True,  False, False),
    ("masters.cost_centre_types","Cost Centre Types","Masters",   24, True,  True,  True,  True,  False, False),
    ("manuals",                 "Manuals",           "Tools",     30, True,  False, False, True,  False, True),
    ("chat",                    "AI Chat",           "Tools",     31, True,  False, False, False, False, False),
    ("health",                  "Health",            "Tools",     32, True,  False, False, False, False, False),
]


def seed_menu(apps, schema_editor):
    CbMenu = apps.get_model("chatbot", "CbMenu")
    for row in SEED_ROWS:
        CbMenu.objects.get_or_create(
            menu_key=row[0],
            defaults={
                "menu_label":       row[1],
                "menu_group":       row[2],
                "menu_order":       row[3],
                "view_available":   row[4],
                "add_available":    row[5],
                "edit_available":   row[6],
                "delete_available": row[7],
                "export_available": row[8],
                "upload_available": row[9],
                "is_active":        True,
            },
        )


def unseed_menu(apps, schema_editor):
    pass  # table will be dropped by the migration reversal


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0002_user_profile_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="CbMenu",
            fields=[
                ("id",               models.AutoField(primary_key=True, serialize=False)),
                ("menu_key",         models.CharField(max_length=60, unique=True)),
                ("menu_label",       models.CharField(max_length=60)),
                ("menu_group",       models.CharField(max_length=40, blank=True)),
                ("menu_order",       models.SmallIntegerField(default=0)),
                ("view_available",   models.BooleanField(default=True)),
                ("add_available",    models.BooleanField(default=False)),
                ("edit_available",   models.BooleanField(default=False)),
                ("delete_available", models.BooleanField(default=False)),
                ("export_available", models.BooleanField(default=False)),
                ("upload_available", models.BooleanField(default=False)),
                ("is_active",        models.BooleanField(default=True)),
                ("cr_dt",            models.DateTimeField(auto_now_add=True)),
                ("mod_dt",           models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "cb_menu", "ordering": ["menu_order", "menu_key"]},
        ),
        migrations.RunPython(seed_menu, unseed_menu),
    ]
