from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prescriptions", "0003_prescription_processing_error"),
    ]

    operations = [
        migrations.AddField(
            model_name="prescriptionmedicine",
            name="confirmation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Review"),
                    ("confirmed", "Confirmed"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]