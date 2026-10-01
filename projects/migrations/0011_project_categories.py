from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_project_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='categories',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
