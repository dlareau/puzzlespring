"""
Backward-compatible data migration for the old global "custom team data" feature.

LIMITATION: the old feature was configured via a single site-wide django-constance
value (TEAM_CUSTOM_DATA_NAME / _DESCRIPTION / _TYPE), which has no history - only
the value as of the time this migration runs is available. This migration applies
that single value retroactively to every hunt that has at least one team with a
non-empty legacy Team.custom_data value. If the site's custom field's name/type
changed over the life of the site, older hunts may end up mislabeled by this
migration and will need manual correction afterward via the new "Team Data
Questions" staff page.

Only the constance database backend's own storage (the `constance.Constance`
table) is read here - NOT `from constance import config` (unsafe/live-registry
inside a migration) and NOT `settings.CONSTANCE_CONFIG` (by the time this
migration runs, the settings-file entries for the old keys have already been
removed in this same release, so they can no longer be used as a source of
defaults). Values not present in the `constance.Constance` table are assumed to
still be at their original hardcoded defaults (empty name = feature never
configured).
"""
from django.db import migrations

# Original defaults from the now-removed CONSTANCE_CONFIG entries.
_DEFAULT_NAME = ''
_DEFAULT_DESCRIPTION = ''
_DEFAULT_TYPE = 'text'


def _get_constance_value(apps, key, default):
    try:
        Constance = apps.get_model('constance', 'Constance')
    except LookupError:
        return default

    from constance.codecs import loads

    row = Constance.objects.filter(key=key).first()
    if row is None or row.value is None:
        return default
    return loads(row.value)


def migrate_custom_data(apps, schema_editor):
    Hunt = apps.get_model('puzzlehunt', 'Hunt')
    TeamDataQuestion = apps.get_model('puzzlehunt', 'TeamDataQuestion')
    TeamDataAnswer = apps.get_model('puzzlehunt', 'TeamDataAnswer')

    name = _get_constance_value(apps, 'TEAM_CUSTOM_DATA_NAME', _DEFAULT_NAME)
    description = _get_constance_value(apps, 'TEAM_CUSTOM_DATA_DESCRIPTION', _DEFAULT_DESCRIPTION)
    data_type = _get_constance_value(apps, 'TEAM_CUSTOM_DATA_TYPE', _DEFAULT_TYPE)

    if not name:
        return

    mapped_type = 'BOOL' if data_type == 'boolean' else 'TEXT'

    # NOTE: a single correlated filter() (not .exclude(), which applies relation-wide
    # for multi-valued reverse relations and would drop a hunt entirely if *any* of its
    # teams has an empty custom_data value) - this matches hunts with at least one team
    # whose custom_data is non-empty.
    hunts_with_data = Hunt.objects.filter(team__custom_data__gt='').distinct()

    for hunt in hunts_with_data:
        question = TeamDataQuestion.objects.create(
            hunt=hunt,
            name=name,
            description=description or '',
            question_type=mapped_type,
            options=[],
            question_order=1,
            required=False,
            visible_on_leaderboard=False,
            used_for_grouping=False,
        )
        TeamDataAnswer.objects.bulk_create([
            TeamDataAnswer(question=question, team=team, value=team.custom_data)
            for team in hunt.team_set.exclude(custom_data='')
        ])


def reverse_migrate_custom_data(apps, schema_editor):
    TeamDataQuestion = apps.get_model('puzzlehunt', 'TeamDataQuestion')
    TeamDataAnswer = apps.get_model('puzzlehunt', 'TeamDataAnswer')

    # Only questions this migration itself could have created follow this exact shape:
    # question_order=1, not visible/grouping, and no options. Restrict the reverse to those,
    # so a manually-added question that happens to share a hunt isn't touched or deleted.
    created_questions = TeamDataQuestion.objects.filter(
        question_order=1, visible_on_leaderboard=False, used_for_grouping=False, options=[]
    )

    for answer in TeamDataAnswer.objects.filter(question__in=created_questions).select_related('team'):
        answer.team.custom_data = answer.value
        answer.team.save(update_fields=['custom_data'])

    created_questions.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('puzzlehunt', '0019_add_team_data_question_answer'),
        # Needed so `apps.get_model('constance', 'Constance')` resolves in the historical
        # apps registry below. Pinned to constance's latest migration as of django-constance
        # 4.3.5; if constance ships new migrations later, this only requires 0003_drop_pickle
        # to have run first, which remains true regardless of later constance migrations.
        ('constance', '0003_drop_pickle'),
    ]

    operations = [
        migrations.RunPython(migrate_custom_data, reverse_migrate_custom_data),
    ]
