from django.db import migrations, models

# group_order controls which group appears first in the permission grid.
# menu_order restarts at 1 within each group.
GROUP_ORDER = {"Overview": 1, "Listings": 2, "Masters": 3, "Tools": 4}

PER_GROUP_ORDERS = {
    "dashboard":               ("Overview", 1),
    "dashboard.operations":    ("Overview", 2),
    "dashboard.hse":           ("Overview", 3),
    "dashboard.workforce":     ("Overview", 4),
    "dashboard.finance":       ("Overview", 5),
    "rigs":                    ("Overview", 6),
    "listings.incidents":      ("Listings", 1),
    "listings.hazard_cards":   ("Listings", 2),
    "listings.employees":      ("Listings", 3),
    "listings.staff":          ("Listings", 4),
    "listings.crew_rotations": ("Listings", 5),
    "listings.invoices":       ("Listings", 6),
    "listings.certificates":   ("Listings", 7),
    "listings.users":          ("Listings", 8),
    "masters.rigs":            ("Masters",  1),
    "masters.operators":       ("Masters",  2),
    "masters.contractors":     ("Masters",  3),
    "masters.cost_centres":    ("Masters",  4),
    "masters.cost_centre_types":("Masters", 5),
    "manuals":                 ("Tools",    1),
    "chat":                    ("Tools",    2),
    "health":                  ("Tools",    3),
}


def apply_group_order(apps, schema_editor):
    CbMenu = apps.get_model("chatbot", "CbMenu")
    for menu_key, (group, order) in PER_GROUP_ORDERS.items():
        CbMenu.objects.filter(menu_key=menu_key).update(
            group_order=GROUP_ORDER[group],
            menu_order=order,
        )


def reverse_group_order(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0003_cb_menu"),
    ]

    operations = [
        migrations.AddField(
            model_name="CbMenu",
            name="group_order",
            field=models.SmallIntegerField(default=0),
        ),
        migrations.RunPython(apply_group_order, reverse_group_order),
    ]
