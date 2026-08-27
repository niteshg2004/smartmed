from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_alter_inventoryhistory_timestamp"),
    ]

    operations = [
        migrations.AlterField(
            model_name="availabilityrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("denied", "Denied"),
                    ("available", "Available"),
                    ("low_stock", "Low Stock"),
                    ("out_of_stock", "Out of Stock"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]