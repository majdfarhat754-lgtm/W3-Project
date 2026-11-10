import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Car",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stock_number", models.CharField(max_length=20, unique=True)),
                ("make", models.CharField(db_index=True, max_length=80)),
                ("model", models.CharField(max_length=100)),
                ("year", models.PositiveSmallIntegerField()),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("mileage", models.PositiveIntegerField()),
                ("transmission", models.CharField(choices=[("Automatic", "Automatic"), ("Manual", "Manual")], max_length=20)),
                ("fuel_type", models.CharField(choices=[("Gasoline", "Gasoline"), ("Diesel", "Diesel"), ("Hybrid", "Hybrid"), ("Electric", "Electric")], max_length=20)),
                ("body_style", models.CharField(blank=True, max_length=40)),
                ("exterior_color", models.CharField(blank=True, max_length=40)),
                ("image_url", models.URLField(max_length=500)),
                ("description", models.TextField(blank=True)),
                ("featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-featured", "-year", "price"],
            },
        ),
    ]
