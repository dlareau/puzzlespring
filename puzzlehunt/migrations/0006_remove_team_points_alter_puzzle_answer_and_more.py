# Generated by Django 4.2 on 2024-08-29 12:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('puzzlehunt', '0005_hintunlockplan_num_hints_alter_hunt_location_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='points',
        ),
        migrations.AlterField(
            model_name='puzzle',
            name='answer',
            field=models.CharField(help_text='The answer to the puzzle.', max_length=100),
        ),
        migrations.AlterField(
            model_name='submission',
            name='user',
            field=models.ForeignKey(help_text='The user who created the submission', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]