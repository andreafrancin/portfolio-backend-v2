from django.db import migrations, models


def copy_text_to_default_language(apps, schema_editor):
    Condition = apps.get_model('billing', 'Condition')
    for condition in Condition.objects.all():
        if condition.text.strip() and not condition.text_i18n:
            condition.text_i18n = {'ca': condition.text}
            condition.save(update_fields=['text_i18n'])


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_totals_style_base'),
    ]

    operations = [
        migrations.AddField(
            model_name='condition',
            name='text_i18n',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(copy_text_to_default_language, migrations.RunPython.noop),
    ]
