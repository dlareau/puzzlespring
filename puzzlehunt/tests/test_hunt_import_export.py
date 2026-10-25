import zipfile

import pytest
from django.urls import reverse

from puzzlehunt.models import Hunt, Puzzle, Round
from puzzlehunt.utils import create_hunt_export_zip, validate_hunt_zip, import_hunt_from_zip

pytestmark = pytest.mark.django_db


def test_import_zip_without_round_files(basic_hunt, tmp_path):
    """A zip exported before rounds existed (no rounds.json / round_statuses.json) still imports."""
    Round.objects.create(hunt=basic_hunt, name="Round One", order_number=1)
    Puzzle.objects.create(id='IMPTST', hunt=basic_hunt, name="Import Puzzle", answer="ANSWER", order_number=1)

    new_zip = tmp_path / "new.zip"
    create_hunt_export_zip(basic_hunt, new_zip, include_activity=True)

    # Rebuild the zip without the round files to mimic an older export
    old_zip = tmp_path / "old.zip"
    with zipfile.ZipFile(new_zip) as src, zipfile.ZipFile(old_zip, 'w') as dst:
        for item in src.infolist():
            if item.filename not in ('rounds.json', 'round_statuses.json'):
                dst.writestr(item, src.read(item.filename))

    basic_hunt.delete()
    validate_hunt_zip(old_zip, include_activity=True)
    hunt = import_hunt_from_zip(old_zip, include_activity=True)

    assert Hunt.objects.filter(pk=hunt.pk).exists()
    assert hunt.puzzle_set.filter(id='IMPTST').exists()
    assert not hunt.round_set.exists()


def test_password_change_page_renders(client, basic_user):
    """The password change page uses the email_backend_configured tag and must render."""
    client.force_login(basic_user)
    response = client.get(reverse('account_change_password'))
    assert response.status_code == 200
