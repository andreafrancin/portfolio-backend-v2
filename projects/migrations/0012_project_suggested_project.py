import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0011_project_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='suggested_project',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='projects.project',
            ),
        ),
    ]
