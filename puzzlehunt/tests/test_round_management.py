import pytest
from django.urls import reverse

from puzzlehunt.models import Puzzle, Round

pytestmark = pytest.mark.django_db


@pytest.fixture
def hunt_with_round(basic_hunt):
    """A hunt with one round holding puzzle 1, plus an unassigned puzzle 2."""
    round_one = Round.objects.create(hunt=basic_hunt, name="Round One", order_number=1)
    Puzzle.objects.create(id='RMGP01', hunt=basic_hunt, round=round_one, name="Alpha", answer="A", order_number=1)
    Puzzle.objects.create(id='RMGP02', hunt=basic_hunt, name="Beta", answer="B", order_number=2)
    return basic_hunt, round_one


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client


def test_create_round_moves_selected_puzzles(staff_client, hunt_with_round):
    """A new round takes the checked puzzles, including one moved out of another round."""
    hunt, round_one = hunt_with_round
    response = staff_client.post(reverse('puzzlehunt:staff:round_create', args=[hunt.pk]),
                                 {'name': "Round Two", 'order_number': 2, 'puzzles': ['RMGP01', 'RMGP02']})

    assert response.status_code == 302
    round_two = Round.objects.get(hunt=hunt, order_number=2)
    assert set(round_two.puzzle_set.values_list('id', flat=True)) == {'RMGP01', 'RMGP02'}
    assert not round_one.puzzle_set.exists()


def test_update_round_removes_unchecked_puzzles(staff_client, hunt_with_round):
    """Unchecking a puzzle takes it out of the round."""
    hunt, round_one = hunt_with_round
    staff_client.post(reverse('puzzlehunt:staff:round_update', args=[hunt.pk, round_one.pk]),
                      {'name': "Renamed", 'order_number': 1})

    round_one.refresh_from_db()
    assert round_one.name == "Renamed"
    assert Puzzle.objects.get(id='RMGP01').round is None


def test_duplicate_round_number_rejected(staff_client, hunt_with_round):
    """Two rounds in a hunt can't share a number."""
    hunt, _ = hunt_with_round
    staff_client.post(reverse('puzzlehunt:staff:round_create', args=[hunt.pk]),
                      {'name': "Duplicate", 'order_number': 1})

    assert hunt.round_set.count() == 1


def test_renumber_round_referenced_by_config_rejected(staff_client, hunt_with_round):
    """Renumbering a round the config refers to would break the config, so it's refused."""
    hunt, round_one = hunt_with_round
    hunt.config = "[R1] <= 0 POINTS"
    hunt.save()

    staff_client.post(reverse('puzzlehunt:staff:round_update', args=[hunt.pk, round_one.pk]),
                      {'name': "Round One", 'order_number': 5, 'puzzles': ['RMGP01']})

    round_one.refresh_from_db()
    assert round_one.order_number == 1


def test_delete_round_referenced_by_config_rejected(staff_client, hunt_with_round):
    """Deleting a round the config refers to is refused."""
    hunt, round_one = hunt_with_round
    hunt.config = "[R1] <= 0 POINTS"
    hunt.save()

    staff_client.post(reverse('puzzlehunt:staff:round_delete', args=[hunt.pk, round_one.pk]))

    assert Round.objects.filter(pk=round_one.pk).exists()


def test_delete_unreferenced_round_unassigns_puzzles(staff_client, hunt_with_round):
    """Deleting a round the config doesn't use removes it and leaves its puzzles in no round."""
    hunt, round_one = hunt_with_round

    staff_client.post(reverse('puzzlehunt:staff:round_delete', args=[hunt.pk, round_one.pk]))

    assert not Round.objects.filter(pk=round_one.pk).exists()
    assert Puzzle.objects.get(id='RMGP01').round is None


def test_rounds_page_renders(staff_client, hunt_with_round):
    """The rounds page lists each round with its puzzles."""
    hunt, _ = hunt_with_round
    response = staff_client.get(reverse('puzzlehunt:staff:hunt_rounds', args=[hunt.pk]))

    assert response.status_code == 200
    assert 'Round One' in response.content.decode()
    assert 'Alpha' in response.content.decode()
