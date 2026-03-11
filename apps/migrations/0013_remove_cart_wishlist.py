from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("apps", "0012_order_user"),
    ]

    operations = [
        migrations.DeleteModel(name="CartItem"),
        migrations.DeleteModel(name="Cart"),
        migrations.DeleteModel(name="Wishlist"),
    ]
