# Generated by Django 4.2.20 on 2025-05-06 00:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('puzzlehunt', '0010_hunt_ratelimit_override_puzzle_ratelimit_override'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hunt',
            name='ratelimit_override',
            field=models.CharField(blank=True, default='', help_text='Override default answer submission rate limit (format: X/YZ, e.g. 3/5m)', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='ratelimit_override',
            field=models.CharField(blank=True, default='', help_text="Override hunt's rate limit (format: X/YZ, e.g. 3/5m)", max_length=20, null=True),
        ),
    ]
