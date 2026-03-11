from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("apps", "0014_remove_user_profile_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("discount_type", models.CharField(choices=[("percent", "Foiz"), ("fixed", "So'm")], default="percent", max_length=10)),
                ("value", models.DecimalField(decimal_places=0, max_digits=10)),
                ("min_total", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("max_discount", models.DecimalField(blank=True, decimal_places=0, max_digits=12, null=True)),
                ("max_uses", models.PositiveIntegerField(blank=True, null=True)),
                ("max_uses_per_user", models.PositiveIntegerField(blank=True, null=True)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="PromoCodeRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_before", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("discount_amount", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("total_after", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("order_ids", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("promo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="redemptions", to="apps.promocode")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="promo_redemptions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
