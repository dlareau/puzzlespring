import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from puzzlehunt.models import Hunt

User = get_user_model()

@pytest.fixture
def basic_hunt():
    """A basic hunt fixture with standard settings."""
    return Hunt.objects.create(
        name="Test Hunt",
        is_current_hunt=True,
        team_size_limit=4,
        start_date=timezone.now(),
        end_date=timezone.now() + timezone.timedelta(days=1),
        display_start_date=timezone.now(),
        display_end_date=timezone.now() + timezone.timedelta(days=1)
    )

@pytest.fixture
def basic_user():
    """A basic user fixture with standard credentials."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123"
    )
