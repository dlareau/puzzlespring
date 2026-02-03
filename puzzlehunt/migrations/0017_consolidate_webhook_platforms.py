# Generated migration to consolidate webhook platform types

from django.db import migrations, models


def convert_platform_types(apps, schema_editor):
    """Convert existing DISC/SLCK/TGRM platforms to WEBHOOK with appropriate format config."""
    NotificationPlatform = apps.get_model('puzzlehunt', 'NotificationPlatform')

    type_to_format = {
        'DISC': 'discord',
        'SLCK': 'slack',
        'TGRM': 'telegram',
    }

    for platform in NotificationPlatform.objects.filter(type__in=type_to_format.keys()):
        old_type = platform.type
        platform.type = 'WHBK'
        platform.config = platform.config or {}
        platform.config['format'] = type_to_format[old_type]
        platform.save()


def reverse_convert_platform_types(apps, schema_editor):
    """Convert WEBHOOK platforms back to their original types based on format config."""
    NotificationPlatform = apps.get_model('puzzlehunt', 'NotificationPlatform')

    format_to_type = {
        'discord': 'DISC',
        'slack': 'SLCK',
        'telegram': 'TGRM',
    }

    for platform in NotificationPlatform.objects.filter(type='WHBK'):
        config = platform.config or {}
        fmt = config.get('format')
        if fmt in format_to_type:
            platform.type = format_to_type[fmt]
            # Remove format from config
            del platform.config['format']
            platform.save()


class Migration(migrations.Migration):

    dependencies = [
        ('puzzlehunt', '0016_create_browser_subscriptions'),
    ]

    operations = [
        # First convert existing platforms to WEBHOOK type
        migrations.RunPython(convert_platform_types, reverse_convert_platform_types),

        # Then update the choices to only include the consolidated types
        migrations.AlterField(
            model_name='notificationplatform',
            name='type',
            field=models.CharField(
                choices=[('BRWS', 'Browser'), ('MAIL', 'Email'), ('WHBK', 'Webhook')],
                help_text='The type of notification platform',
                max_length=4
            ),
        ),
    ]
