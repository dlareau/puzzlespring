from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from puzzlehunt.models import Hunt
from django.contrib.sites.models import Site
from datetime import timedelta
import os

class Command(BaseCommand):
    help = 'Performs initial setup: creates the first hunt, collects static files, and creates a superuser'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            '\nWARNING: This command will delete all existing data and set up a fresh instance.'
            '\nThis should only be run on initial setup.'
            '\nAre you sure you want to continue? (yes/no): '
        ))
        
        if input().lower() != 'yes':
            self.stdout.write(self.style.ERROR('Setup cancelled.'))
            return

        self.stdout.write('Starting initial setup...')

        # Flush existing data
        self.stdout.write('Flushing existing data...')
        try:
            call_command('flush', interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS('Successfully flushed existing data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to flush data: {str(e)}'))
            return

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

        # Update site domain
        self.stdout.write('Updating site domain...')
        try:
            domain = os.environ.get('DOMAIN', 'example.com')  # Default to example.com if no domain set
            # Remove port if present
            domain = domain.split(':')[0]
            site, created = Site.objects.get_or_create(
                id=1,
                defaults={
                    'domain': domain,
                    'name': domain
                }
            )
            if not created:
                site.domain = domain
                site.name = domain
                site.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated site domain to {domain}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to update site domain: {str(e)}'))

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