# Generated migration to refactor access control

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_candidateentry_is_waiting'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='event_access_password',
        ),
        migrations.RemoveField(
            model_name='round',
            name='access_password',
        ),
        migrations.RemoveField(
            model_name='round',
            name='owner_email',
        ),
        migrations.AddField(
            model_name='round',
            name='access_code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
