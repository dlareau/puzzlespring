# Generated by Django 4.2 on 2024-12-31 02:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('puzzlehunt', '0016_hunt_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='num_total_hints_earned',
            field=models.IntegerField(default=0, help_text='The total number of hints this team has earned through config rules'),
        ),
        migrations.AddField(
            model_name='team',
            name='points',
            field=models.IntegerField(default=0, help_text='The total number of points this team has earned through config rules'),
        ),
        migrations.AlterField(
            model_name='hunt',
            name='hint_lockout',
            field=models.IntegerField(default=60, help_text='Time (in minutes) teams must wait before a hint can be used on a newly unlocked puzzle'),
        ),
        migrations.AlterField(
            model_name='team',
            name='num_available_hints',
            field=models.IntegerField(default=0, help_text='The number of hints the team currently has available to use'),
        ),
        migrations.DeleteModel(
            name='HintUnlockPlan',
        ),
    ]