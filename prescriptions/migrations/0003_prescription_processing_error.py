from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prescriptions", "0002_alter_prescription_uploaded_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="prescription",
            name="processing_error",
            field=models.TextField(
                blank=True,
                help_text="Human-readable processing failure reason (e.g. OCR unavailable).",
            ),
        ),
    ]
