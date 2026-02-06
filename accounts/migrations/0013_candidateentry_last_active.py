# Generated migration

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_update_access_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidateentry',
            name='last_active',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
