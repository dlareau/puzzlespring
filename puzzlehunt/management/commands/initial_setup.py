from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from puzzlehunt.models import Hunt
from datetime import timedelta

class Command(BaseCommand):
    help = 'Performs initial setup: creates the first hunt, collects static files, and creates a superuser'

    def handle(self, *args, **options):
        self.stdout.write('Starting initial setup...')

        # Create initial hunt
        self.stdout.write('Creating initial hunt...')
        now = timezone.now()
        try:
            Hunt.objects.create(
                name="First Hunt",
                team_size_limit=4,
                start_date=now,
                end_date=now + timedelta(days=7),
                display_start_date=now,
                display_end_date=now + timedelta(days=7),
                location="TBD",
                is_current_hunt=True,
                hint_lockout=60
            )
            self.stdout.write(self.style.SUCCESS('Successfully created initial hunt'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create hunt: {str(e)}'))
            return

        # Collect static files
        self.stdout.write('Collecting static files...')
        try:
            call_command('collectstatic', interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS('Successfully collected static files'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to collect static files: {str(e)}'))
            return

        # Create superuser
        self.stdout.write('Setting up superuser...')
        try:
            call_command('createsuperuser')
            self.stdout.write(self.style.SUCCESS('Successfully created superuser'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create superuser: {str(e)}'))
            return

        self.stdout.write(self.style.SUCCESS('\nInitial setup completed successfully!')) 