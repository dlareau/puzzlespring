import os

import pytest
from django.conf import settings as django_settings
from django.urls import reverse

from puzzlehunt.models import Puzzle, Round

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_rounds(basic_hunt):
    """Two rounds, each with one puzzle."""
    round_one = Round.objects.create(hunt=basic_hunt, name="Round One", order_number=1)
    round_two = Round.objects.create(hunt=basic_hunt, name="Round Two", order_number=2)
    Puzzle.objects.create(id='RNDP01', hunt=basic_hunt, round=round_one, name="Alpha", answer="A", order_number=1)
    Puzzle.objects.create(id='RNDP02', hunt=basic_hunt, round=round_one, name="Beta", answer="B", order_number=2)
    Puzzle.objects.create(id='RNDP03', hunt=basic_hunt, round=round_two, name="Gamma", answer="C", order_number=3)
    return round_one, round_two


PREVIEW_TEMPLATE = "{% for p in puzzles %}[{{ p.name }}]{% endfor %}|{% for r in rounds %}[{{ r.name }}]{% endfor %}"


def test_save_round_template_writes_round_not_hunt(client, staff_user, basic_hunt, two_rounds):
    """Saving with ?round= stores the template on that round and leaves the hunt template alone."""
    round_one, _ = two_rounds
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:hunt_template', args=[basic_hunt.pk]) + '?round=1'

    response = client.post(url, {'template_text': '<p>Round one page</p>'})

    assert response.status_code == 200
    round_one.refresh_from_db()
    basic_hunt.refresh_from_db()
    assert round_one.template_file.read().decode() == '<p>Round one page</p>'
    assert not basic_hunt.template_file


def test_preview_round_template_filters_puzzles_and_rounds(client, staff_user, basic_hunt, two_rounds):
    """Round preview shows only the round's puzzles marked unlocked, and only the rounds marked unlocked."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:preview_round_template', args=[basic_hunt.pk, 1])

    # Puzzle 3 is unlocked but belongs to round two, so the round one preview must leave it out
    response = client.post(url, {
        'template_text': PREVIEW_TEMPLATE,
        'unlocked': '1, 3',
        'solved': '',
        'unlocked_rounds': '2',
    })

    assert response.content.decode() == "[Alpha]|[Round Two]"


def test_preview_hunt_template_filters_rounds(client, staff_user, basic_hunt, two_rounds):
    """Hunt preview gets the rounds marked unlocked, like the live hunt page does."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:preview_template', args=[basic_hunt.pk])

    response = client.post(url, {
        'template_text': PREVIEW_TEMPLATE,
        'unlocked': '1, 3',
        'solved': '',
        'unlocked_rounds': '1',
    })

    assert response.content.decode() == "[Alpha][Gamma]|[Round One]"


def test_round_view_renders_saved_template(client, settings, staff_user, basic_hunt, two_rounds):
    """A round with a saved template renders that template instead of the default round page."""
    # Production template DIRS point at /app/media/trusted/; point them at the test media root instead
    settings.TEMPLATES = [{
        **django_settings.TEMPLATES[0],
        'DIRS': [os.path.join(settings.MEDIA_ROOT, 'trusted')],
    }]
    client.force_login(staff_user)
    client.post(reverse('puzzlehunt:staff:hunt_template', args=[basic_hunt.pk]) + '?round=1',
                {'template_text': '<p>Custom round {{ round.name }}</p>'})

    response = client.get(reverse('puzzlehunt:round_view', args=[basic_hunt.pk, 1]))

    assert response.status_code == 200
    assert '<p>Custom round Round One</p>' in response.content.decode()
