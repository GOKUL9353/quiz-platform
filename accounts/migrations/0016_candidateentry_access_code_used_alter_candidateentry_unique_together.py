# Generated migration file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_candidateentry_score_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidateentry',
            name='access_code_used',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='candidateentry',
            unique_together={('round', 'candidate_name', 'access_code_used')},
        ),
    ]
