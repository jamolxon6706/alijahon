from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("apps", "0013_remove_cart_wishlist"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="district",
        ),
        migrations.RemoveField(
            model_name="user",
            name="telegram_id",
        ),
        migrations.RemoveField(
            model_name="user",
            name="description",
        ),
        migrations.DeleteModel(
            name="District",
        ),
        migrations.DeleteModel(
            name="Region",
        ),
    ]
