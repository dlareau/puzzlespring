import pytest
from django.urls import reverse
from django.core.files.base import ContentFile
from puzzlehunt.models import Hunt, Puzzle, PuzzleFile, SolutionFile, HuntFile

pytestmark = pytest.mark.django_db


@pytest.fixture
def puzzle_with_file(basic_hunt):
    """Create a puzzle with an editable HTML file."""
    puzzle = Puzzle.objects.create(
        id='FEDTST',
        hunt=basic_hunt,
        name="File Editor Test Puzzle",
        answer="ANSWER",
        order_number=1
    )
    # Create a PuzzleFile with .html extension (text-editable)
    puzzle_file = PuzzleFile(parent=puzzle)
    puzzle_file.file.save('test.html', ContentFile(b'<html><body>Test Content</body></html>'))
    return puzzle


@pytest.fixture
def puzzle_with_solution_file(basic_hunt):
    """Create a puzzle with an editable solution file."""
    puzzle = Puzzle.objects.create(
        id='FEDSOL',
        hunt=basic_hunt,
        name="Solution Test Puzzle",
        answer="SOLUTIONANSWER",
        order_number=2
    )
    # Create a SolutionFile with .html extension (text-editable)
    solution_file = SolutionFile(parent=puzzle)
    solution_file.file.save('solution.html', ContentFile(b'<html><body>Solution</body></html>'))
    return puzzle


@pytest.fixture
def hunt_with_file(basic_hunt):
    """Add a text-editable file to the basic hunt."""
    hunt_file = HuntFile(parent=basic_hunt)
    hunt_file.file.save('styles.css', ContentFile(b'body { color: black; }'))
    return basic_hunt


@pytest.fixture
def puzzle_with_non_editable_file(basic_hunt):
    """Create a puzzle with a non-editable file (e.g., image)."""
    puzzle = Puzzle.objects.create(
        id='FEDIMG',
        hunt=basic_hunt,
        name="Image Test Puzzle",
        answer="IMAGE",
        order_number=3
    )
    # Create a PuzzleFile with .png extension (not text-editable)
    puzzle_file = PuzzleFile(parent=puzzle)
    puzzle_file.file.save('image.png', ContentFile(b'\x89PNG\r\n\x1a\n'))
    return puzzle


# =============================================================================
# Authentication/Authorization Tests
# =============================================================================

def test_file_editor_non_staff_redirected(client, basic_user, basic_hunt):
    """Test that non-staff user is redirected when accessing file editor."""
    client.force_login(basic_user)
    url = reverse('puzzlehunt:staff:file_editor', args=[basic_hunt.pk])
    response = client.get(url)
    assert response.status_code == 302
    assert '/admin/login/' in response.url


def test_file_editor_staff_can_access(client, staff_user, basic_hunt):
    """Test that staff user can access file editor."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor', args=[basic_hunt.pk])
    response = client.get(url)
    assert response.status_code == 200


def test_file_editor_unauthenticated_redirected(client, basic_hunt):
    """Test that unauthenticated user is redirected when accessing file editor."""
    url = reverse('puzzlehunt:staff:file_editor', args=[basic_hunt.pk])
    response = client.get(url)
    assert response.status_code == 302


# =============================================================================
# Main Page Tests
# =============================================================================

def test_file_editor_loads_empty_state(client, staff_user, basic_hunt):
    """Test that file editor loads normally with empty state."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor', args=[basic_hunt.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert 'hunt' in response.context
    assert response.context['hunt'] == basic_hunt


def test_file_editor_context_includes_hunts(client, staff_user, basic_hunt):
    """Test that file editor context includes list of hunts."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor', args=[basic_hunt.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert 'hunts' in response.context
    assert basic_hunt in response.context['hunts']


def test_file_editor_preselect_puzzle_file(client, staff_user, puzzle_with_file):
    """Test that file editor can preselect a puzzle file via query params."""
    client.force_login(staff_user)
    puzzle = puzzle_with_file
    puzzle_file = puzzle.files.first()

    url = reverse('puzzlehunt:staff:file_editor', args=[puzzle.hunt.pk])
    response = client.get(url, {
        'type': 'puzzle',
        'parent': puzzle.pk,
        'file': puzzle_file.pk
    })

    assert response.status_code == 200
    assert 'content' in response.context
    assert response.context['content'] is not None
    assert 'Test Content' in response.context['content']
    assert response.context['selected_file_pk'] == puzzle_file.pk


def test_file_editor_preselect_hunt_file(client, staff_user, hunt_with_file):
    """Test that file editor can preselect a hunt file via query params."""
    client.force_login(staff_user)
    hunt = hunt_with_file
    hunt_file = hunt.files.first()

    url = reverse('puzzlehunt:staff:file_editor', args=[hunt.pk])
    response = client.get(url, {
        'type': 'hunt',
        'parent': hunt.pk,
        'file': hunt_file.pk
    })

    assert response.status_code == 200
    assert 'content' in response.context
    assert response.context['content'] is not None
    assert 'color: black' in response.context['content']
    assert response.context['selected_file_pk'] == hunt_file.pk


def test_file_editor_shows_puzzles_with_files(client, staff_user, puzzle_with_file):
    """Test that file editor context includes puzzles that have editable files."""
    client.force_login(staff_user)
    puzzle = puzzle_with_file
    puzzle_file = puzzle.files.first()

    url = reverse('puzzlehunt:staff:file_editor', args=[puzzle.hunt.pk])
    response = client.get(url, {
        'type': 'puzzle',
        'parent': puzzle.pk,
        'file': puzzle_file.pk
    })

    assert response.status_code == 200
    assert 'puzzles' in response.context
    assert puzzle in response.context['puzzles']


def test_file_editor_shows_hunt_has_files(client, staff_user, hunt_with_file):
    """Test that file editor context indicates hunt has editable files."""
    client.force_login(staff_user)
    hunt = hunt_with_file
    hunt_file = hunt.files.first()

    url = reverse('puzzlehunt:staff:file_editor', args=[hunt.pk])
    response = client.get(url, {
        'type': 'hunt',
        'parent': hunt.pk,
        'file': hunt_file.pk
    })

    assert response.status_code == 200
    assert 'hunt_has_files' in response.context
    assert response.context['hunt_has_files'] is True


# =============================================================================
# HTMX Endpoint Tests - file_editor_puzzle_list
# =============================================================================

def test_file_editor_puzzle_list_returns_puzzles(client, staff_user, puzzle_with_file):
    """Test that puzzle list endpoint returns puzzles with editable files."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_puzzle_list')
    response = client.get(url, {'hunt_id': puzzle_with_file.hunt.pk}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'puzzles' in response.context
    assert puzzle_with_file in response.context['puzzles']


def test_file_editor_puzzle_list_empty_without_hunt_id(client, staff_user):
    """Test that puzzle list endpoint returns empty when no hunt_id provided."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_puzzle_list')
    response = client.get(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['puzzles'] == []
    assert response.context['hunt'] is None


def test_file_editor_puzzle_list_includes_hunt_files_flag(client, staff_user, hunt_with_file, puzzle_with_file):
    """Test that puzzle list endpoint includes hunt_has_files flag."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_puzzle_list')
    response = client.get(url, {'hunt_id': hunt_with_file.pk}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['hunt_has_files'] is True


# =============================================================================
# HTMX Endpoint Tests - file_editor_file_list
# =============================================================================

def test_file_editor_file_list_returns_puzzle_files(client, staff_user, puzzle_with_file):
    """Test that file list endpoint returns files for a puzzle."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_file_list')
    response = client.get(url, {'parent': f'puzzle:{puzzle_with_file.pk}'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'file_entries' in response.context
    assert len(response.context['file_entries']) > 0
    assert response.context['file_entries'][0]['file_type'] == 'puzzle'


def test_file_editor_file_list_returns_solution_files(client, staff_user, puzzle_with_solution_file):
    """Test that file list endpoint returns solution files for a puzzle."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_file_list')
    response = client.get(url, {'parent': f'puzzle:{puzzle_with_solution_file.pk}'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'file_entries' in response.context
    assert len(response.context['file_entries']) > 0
    # Solution files should be included
    file_types = [entry['file_type'] for entry in response.context['file_entries']]
    assert 'solution' in file_types


def test_file_editor_file_list_returns_hunt_files(client, staff_user, hunt_with_file):
    """Test that file list endpoint returns files for a hunt."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_file_list')
    response = client.get(url, {'parent': f'hunt:{hunt_with_file.pk}'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'file_entries' in response.context
    assert len(response.context['file_entries']) > 0
    assert response.context['file_entries'][0]['file_type'] == 'hunt'


def test_file_editor_file_list_empty_without_parent(client, staff_user):
    """Test that file list endpoint returns empty when no parent provided."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_file_list')
    response = client.get(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['file_entries'] == []


def test_file_editor_file_list_empty_with_invalid_parent(client, staff_user):
    """Test that file list endpoint returns empty when invalid parent provided."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_file_list')
    response = client.get(url, {'parent': 'invalid'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['file_entries'] == []


# =============================================================================
# HTMX Endpoint Tests - file_editor_load_content
# =============================================================================

def test_file_editor_load_content_returns_file_content(client, staff_user, puzzle_with_file):
    """Test that load content endpoint returns file content for valid file."""
    client.force_login(staff_user)
    puzzle_file = puzzle_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_editor_load_content')
    response = client.get(url, {'file': f'puzzle:{puzzle_file.pk}'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'content' in response.context
    assert 'Test Content' in response.context['content']
    assert response.context['file'] == puzzle_file


def test_file_editor_load_content_returns_hunt_file_content(client, staff_user, hunt_with_file):
    """Test that load content endpoint returns content for hunt file."""
    client.force_login(staff_user)
    hunt_file = hunt_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_editor_load_content')
    response = client.get(url, {'file': f'hunt:{hunt_file.pk}'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert 'content' in response.context
    assert 'color: black' in response.context['content']


def test_file_editor_load_content_empty_without_file(client, staff_user):
    """Test that load content endpoint returns empty editor when no file provided."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_load_content')
    response = client.get(url, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['file'] is None


def test_file_editor_load_content_empty_with_invalid_file(client, staff_user):
    """Test that load content endpoint returns empty editor when invalid file provided."""
    client.force_login(staff_user)
    url = reverse('puzzlehunt:staff:file_editor_load_content')
    response = client.get(url, {'file': 'invalid'}, HTTP_HX_REQUEST='true')

    assert response.status_code == 200
    assert response.context['file'] is None


# =============================================================================
# File Save Tests
# =============================================================================

def test_file_save_content_success_puzzle_file(client, staff_user, puzzle_with_file):
    """Test successfully saving content to a puzzle file."""
    client.force_login(staff_user)
    puzzle_file = puzzle_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['puzzle', puzzle_file.pk])

    new_content = '<html><body>Updated Content</body></html>'
    response = client.post(url, {'content': new_content})

    assert response.status_code == 200
    assert response.json()['success'] is True

    # Verify the file content was actually updated
    puzzle_file.refresh_from_db()
    puzzle_file.file.open('r')
    saved_content = puzzle_file.file.read()
    puzzle_file.file.close()
    assert 'Updated Content' in saved_content


def test_file_save_content_success_hunt_file(client, staff_user, hunt_with_file):
    """Test successfully saving content to a hunt file."""
    client.force_login(staff_user)
    hunt_file = hunt_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['hunt', hunt_file.pk])

    new_content = 'body { color: red; }'
    response = client.post(url, {'content': new_content})

    assert response.status_code == 200
    assert response.json()['success'] is True

    # Verify the file content was actually updated
    hunt_file.refresh_from_db()
    hunt_file.file.open('r')
    saved_content = hunt_file.file.read()
    hunt_file.file.close()
    assert 'color: red' in saved_content


def test_file_save_content_non_text_editable_returns_400(client, staff_user, puzzle_with_non_editable_file):
    """Test that saving to a non-text-editable file returns 400."""
    client.force_login(staff_user)
    puzzle_file = puzzle_with_non_editable_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['puzzle', puzzle_file.pk])

    response = client.post(url, {'content': 'some content'})

    assert response.status_code == 400
    assert 'error' in response.json()


def test_file_save_content_non_staff_denied(client, basic_user, puzzle_with_file):
    """Test that non-staff user is denied access to file save."""
    client.force_login(basic_user)
    puzzle_file = puzzle_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['puzzle', puzzle_file.pk])

    response = client.post(url, {'content': 'hacked content'})

    assert response.status_code == 302
    assert '/admin/login/' in response.url


def test_file_save_content_unauthenticated_denied(client, puzzle_with_file):
    """Test that unauthenticated user is denied access to file save."""
    puzzle_file = puzzle_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['puzzle', puzzle_file.pk])

    response = client.post(url, {'content': 'hacked content'})

    assert response.status_code == 302


def test_file_save_content_returns_saved_timestamp(client, staff_user, puzzle_with_file):
    """Test that file save returns a saved_at timestamp."""
    client.force_login(staff_user)
    puzzle_file = puzzle_with_file.files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['puzzle', puzzle_file.pk])

    response = client.post(url, {'content': 'new content'})

    assert response.status_code == 200
    assert 'saved_at' in response.json()


def test_file_save_content_solution_file(client, staff_user, puzzle_with_solution_file):
    """Test successfully saving content to a solution file."""
    client.force_login(staff_user)
    solution_file = puzzle_with_solution_file.solution_files.first()
    url = reverse('puzzlehunt:staff:file_save_content', args=['solution', solution_file.pk])

    new_content = '<html><body>Updated Solution</body></html>'
    response = client.post(url, {'content': new_content})

    assert response.status_code == 200
    assert response.json()['success'] is True

    # Verify the file content was actually updated
    solution_file.refresh_from_db()
    solution_file.file.open('r')
    saved_content = solution_file.file.read()
    solution_file.file.close()
    assert 'Updated Solution' in saved_content
