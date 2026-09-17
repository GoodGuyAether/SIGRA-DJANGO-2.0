from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("resoluciones", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="resolucionmateria",
            name="situacion",
            field=models.CharField(
                choices=[("corresponde", "Corresponde"), ("no_corresponde", "No corresponde")],
                default="corresponde",
                max_length=20,
            ),
        ),
    ]
