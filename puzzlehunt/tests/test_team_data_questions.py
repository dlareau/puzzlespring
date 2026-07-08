import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from puzzlehunt.models import Hunt, Team, TeamDataAnswer, TeamDataQuestion

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_hunt():
    """A second hunt, independent from basic_hunt, used for isolation checks."""
    return Hunt.objects.create(
        name="Other Hunt",
        is_current_hunt=False,
        team_size_limit=4,
        start_date=timezone.now(),
        end_date=timezone.now() + timezone.timedelta(days=1),
    )


# --- Model behavior ---

def test_question_creation(basic_hunt):
    question = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Fun Fact", question_type=TeamDataQuestion.QuestionType.TEXT, question_order=1
    )
    assert question.hunt == basic_hunt
    assert question.question_type == "TEXT"


def test_question_order_unique_per_hunt(basic_hunt):
    TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    with pytest.raises(ValidationError):
        q2 = TeamDataQuestion(hunt=basic_hunt, name="Q2", question_order=1)
        q2.full_clean()


def test_question_order_can_repeat_across_hunts(basic_hunt, other_hunt):
    TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    # Should not raise - question_order is only unique within a hunt
    TeamDataQuestion.objects.create(hunt=other_hunt, name="Q1", question_order=1)


def test_select_question_requires_options(basic_hunt):
    question = TeamDataQuestion(
        hunt=basic_hunt, name="Size", question_type=TeamDataQuestion.QuestionType.SELECT,
        question_order=1, options=[]
    )
    with pytest.raises(ValidationError):
        question.full_clean()


def test_non_select_question_rejects_options(basic_hunt):
    question = TeamDataQuestion(
        hunt=basic_hunt, name="Fun Fact", question_type=TeamDataQuestion.QuestionType.TEXT,
        question_order=1, options=["A", "B"]
    )
    with pytest.raises(ValidationError):
        question.full_clean()


def test_answer_unique_per_question_and_team(basic_hunt):
    question = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    team = Team.objects.create(name="Team A", hunt=basic_hunt)
    TeamDataAnswer.objects.create(question=question, team=team, value="hello")
    with pytest.raises(ValidationError):
        answer = TeamDataAnswer(question=question, team=team, value="world")
        answer.full_clean()


def test_deleting_question_cascades_to_answers(basic_hunt):
    question = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    team = Team.objects.create(name="Team A", hunt=basic_hunt)
    TeamDataAnswer.objects.create(question=question, team=team, value="hello")
    question.delete()
    assert TeamDataAnswer.objects.count() == 0


def test_deleting_team_cascades_to_answers(basic_hunt):
    question = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    team = Team.objects.create(name="Team A", hunt=basic_hunt)
    TeamDataAnswer.objects.create(question=question, team=team, value="hello")
    team.delete()
    assert TeamDataAnswer.objects.count() == 0


def test_boolean_answer_display_value(basic_hunt):
    question = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="First timer?", question_type=TeamDataQuestion.QuestionType.BOOLEAN, question_order=1
    )
    team = Team.objects.create(name="Team A", hunt=basic_hunt)
    yes = TeamDataAnswer.objects.create(question=question, team=team, value="True")
    assert yes.display_value == "Yes"


# --- Registration form / per-hunt isolation ---

def test_registration_form_only_shows_questions_for_current_hunt(client, basic_hunt, other_hunt, basic_user):
    TeamDataQuestion.objects.create(hunt=basic_hunt, name="Current Hunt Question", question_order=1)
    TeamDataQuestion.objects.create(hunt=other_hunt, name="Other Hunt Question", question_order=1)

    client.force_login(basic_user)
    response = client.get(reverse('puzzlehunt:team_create'))
    content = response.content.decode()
    assert "Current Hunt Question" in content
    assert "Other Hunt Question" not in content


def test_registration_rejects_invalid_select_option(client, basic_hunt, basic_user):
    question = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Shirt Size", question_type=TeamDataQuestion.QuestionType.SELECT,
        options=["S", "M", "L"], question_order=1, required=True
    )
    client.force_login(basic_user)
    response = client.post(reverse('puzzlehunt:team_create'), {
        'name': 'Test Team',
        f'question_{question.pk}': 'XL',  # not a valid option
    })
    assert response.status_code == 200
    assert not Team.objects.filter(name='Test Team').exists()


def test_registration_saves_multiple_question_types(client, basic_hunt, basic_user):
    q_text = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Motto", question_order=1)
    q_bool = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="First timer?", question_type=TeamDataQuestion.QuestionType.BOOLEAN, question_order=2
    )
    q_sel = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Size", question_type=TeamDataQuestion.QuestionType.SELECT,
        options=["S", "M", "L"], question_order=3
    )

    client.force_login(basic_user)
    response = client.post(reverse('puzzlehunt:team_create'), {
        'name': 'Multi Team',
        f'question_{q_text.pk}': 'Puzzles are fun',
        f'question_{q_bool.pk}': 'on',
        f'question_{q_sel.pk}': 'M',
    })
    assert response.status_code == 302

    team = Team.objects.get(name='Multi Team')
    answers = {a.question_id: a.value for a in team.teamdataanswer_set.all()}
    assert answers[q_text.pk] == 'Puzzles are fun'
    assert answers[q_bool.pk] == 'True'
    assert answers[q_sel.pk] == 'M'


# --- Staff CRUD views ---

def test_staff_can_create_question(client, basic_hunt, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse('puzzlehunt:staff:team_data_question_create', args=[basic_hunt.pk]),
        {'name': 'Dietary Restrictions', 'question_type': 'TEXT'},
    )
    assert response.status_code in (200, 302)
    assert TeamDataQuestion.objects.filter(hunt=basic_hunt, name='Dietary Restrictions').exists()


def test_non_staff_cannot_create_question(client, basic_hunt, basic_user):
    client.force_login(basic_user)
    response = client.post(
        reverse('puzzlehunt:staff:team_data_question_create', args=[basic_hunt.pk]),
        {'name': 'Dietary Restrictions', 'question_type': 'TEXT'},
    )
    assert response.status_code in (302, 403)
    assert not TeamDataQuestion.objects.filter(hunt=basic_hunt).exists()


def test_staff_create_select_without_options_is_rejected(client, basic_hunt, staff_user):
    client.force_login(staff_user)
    client.post(
        reverse('puzzlehunt:staff:team_data_question_create', args=[basic_hunt.pk]),
        {'name': 'Size', 'question_type': 'SEL', 'options': ''},
    )
    assert not TeamDataQuestion.objects.filter(hunt=basic_hunt, name='Size').exists()


def test_staff_update_question(client, basic_hunt, staff_user):
    question = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Old Name", question_order=1)
    client.force_login(staff_user)
    client.post(
        reverse('puzzlehunt:staff:team_data_question_update', args=[basic_hunt.pk, question.pk]),
        {'name': 'New Name', 'question_type': 'TEXT'},
    )
    question.refresh_from_db()
    assert question.name == 'New Name'


def test_staff_delete_question(client, basic_hunt, staff_user):
    question = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    client.force_login(staff_user)
    client.post(reverse('puzzlehunt:staff:team_data_question_delete', args=[basic_hunt.pk, question.pk]))
    assert not TeamDataQuestion.objects.filter(pk=question.pk).exists()


def test_staff_move_question_swaps_order(client, basic_hunt, staff_user):
    q1 = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1)
    q2 = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q2", question_order=2)

    client.force_login(staff_user)
    client.post(
        reverse('puzzlehunt:staff:team_data_question_move', args=[basic_hunt.pk, q2.pk]),
        {'direction': 'up'},
    )
    q1.refresh_from_db()
    q2.refresh_from_db()
    assert q2.question_order == 1
    assert q1.question_order == 2


def test_used_for_grouping_is_exclusive_per_hunt(client, basic_hunt, staff_user):
    q1 = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q1", question_order=1, used_for_grouping=True)
    q2 = TeamDataQuestion.objects.create(hunt=basic_hunt, name="Q2", question_order=2)

    client.force_login(staff_user)
    client.post(
        reverse('puzzlehunt:staff:team_data_question_update', args=[basic_hunt.pk, q2.pk]),
        {'name': 'Q2', 'question_type': 'TEXT', 'used_for_grouping': 'on'},
    )
    q1.refresh_from_db()
    q2.refresh_from_db()
    assert q1.used_for_grouping is False
    assert q2.used_for_grouping is True


# --- Leaderboard ---

def test_leaderboard_shows_visible_columns_only(client, basic_hunt, basic_user):
    TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Shown Question", question_order=1, visible_on_leaderboard=True
    )
    TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Hidden Question", question_order=2, visible_on_leaderboard=False
    )
    Team.objects.create(name="Team A", hunt=basic_hunt)

    client.force_login(basic_user)
    response = client.get(reverse('puzzlehunt:hunt_leaderboard', args=[basic_hunt.pk]))
    content = response.content.decode()
    assert "Shown Question" in content
    assert "Hidden Question" not in content


def test_leaderboard_groups_by_select_question(client, basic_hunt, basic_user):
    question = TeamDataQuestion.objects.create(
        hunt=basic_hunt, name="Division", question_type=TeamDataQuestion.QuestionType.SELECT,
        options=["Rookie", "Veteran"], question_order=1, used_for_grouping=True
    )
    t1 = Team.objects.create(name="Team A", hunt=basic_hunt)
    t2 = Team.objects.create(name="Team B", hunt=basic_hunt)
    TeamDataAnswer.objects.create(question=question, team=t1, value="Rookie")
    TeamDataAnswer.objects.create(question=question, team=t2, value="Veteran")

    client.force_login(basic_user)
    response = client.get(reverse('puzzlehunt:hunt_leaderboard', args=[basic_hunt.pk]))
    content = response.content.decode()
    assert "Grouped by Division" in content
    assert "Rookie" in content
    assert "Veteran" in content


def test_leaderboard_no_grouping_when_no_question_configured(client, basic_hunt, basic_user):
    Team.objects.create(name="Team A", hunt=basic_hunt)
    client.force_login(basic_user)
    response = client.get(reverse('puzzlehunt:hunt_leaderboard', args=[basic_hunt.pk]))
    content = response.content.decode()
    assert "Grouped by" not in content
