from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from puzzlehunt.utils import import_hunt_from_zip
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
import os
from puzzlehunt.models import Team

User = get_user_model()

class Command(BaseCommand):
    help = 'Sets up a load test environment by importing a test hunt and creating test users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--num-users',
            type=int,
            default=100,
            help='Number of test users to create (default: 100)'
        )
        parser.add_argument(
            '--team-size',
            type=int,
            default=4,
            help='Number of users per team (default: 4)'
        )
        parser.add_argument(
            '--num-staff',
            type=int,
            default=10,
            help='Number of staff users to create (default: 10)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            '\nWARNING: This command will delete all existing data and set up a fresh load test instance.'
            '\nThis should only be run in development or testing environments.'
            '\nAre you sure you want to continue? (yes/no): '
        ))
        
        if input().lower() != 'yes':
            self.stdout.write(self.style.ERROR('Load test setup cancelled.'))
            return

        self.stdout.write('Starting load test setup...')

        # Flush existing data
        self.stdout.write('Flushing existing data...')
        try:
            call_command('flush', interactive=False, verbosity=0)
            self.stdout.write(self.style.SUCCESS('Successfully flushed existing data'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to flush data: {str(e)}'))
            return

        # Import the load test hunt
        self.stdout.write('Importing load test hunt...')
        try:
            hunt_file = Path('locust/LoadTest.phe')
            if not hunt_file.exists():
                self.stdout.write(self.style.ERROR(f'Hunt file not found at {hunt_file}'))
                return
            
            hunt = import_hunt_from_zip(hunt_file)
            hunt.is_current_hunt = True
            hunt.start_date = timezone.now()
            hunt.end_date = timezone.now() + timedelta(days=3)
            hunt.save()
            self.stdout.write(self.style.SUCCESS('Successfully imported load test hunt'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to import hunt: {str(e)}'))
            return

        # Create test users
        self.stdout.write(f'Creating {options["num_users"]} test users...')
        try:
            for i in range(options["num_users"]):
                User.objects.create_user(
                    email=f'test{i}@example.com',
                    password='test',
                    display_name=f'Test User {i}',
                    first_name=f'Test{i}',
                    last_name='User'
                )
            self.stdout.write(self.style.SUCCESS('Successfully created test users'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create users: {str(e)}'))
            return

        # Create teams and assign users
        num_teams = (options["num_users"] + options["team_size"] - 1) // options["team_size"]
        self.stdout.write(f'Creating {num_teams} teams...')
        
        users = list(User.objects.filter(email__startswith='test'))
        try:
            for i in range(num_teams):
                team = Team.objects.create(
                    hunt=hunt,
                    name=f'Test Team {i}',
                    join_code=f'TEST{i:04d}'
                )
                
                # Assign users to this team
                start_idx = i * options["team_size"]
                end_idx = min(start_idx + options["team_size"], len(users))
                team_users = users[start_idx:end_idx]
                
                for user in team_users:
                    team.members.add(user)
                
            self.stdout.write(self.style.SUCCESS('Successfully created teams'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create teams: {str(e)}'))
            return

        # Create staff users
        self.stdout.write(f'Creating {options["num_staff"]} staff users...')
        try:
            for i in range(options["num_staff"]):
                User.objects.create_user(
                    email=f'staff{i}@example.com',
                    password='test',
                    display_name=f'Staff User {i}',
                    first_name=f'Staff{i}',
                    last_name='User',
                    is_staff=True
                )
            self.stdout.write(self.style.SUCCESS('Successfully created staff users'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create staff users: {str(e)}'))
            return

        # Create superuser for load testing
        self.stdout.write('Creating load test superuser...')
        try:
            User.objects.create_superuser(
                email='locust@test.com',
                password='locust',
                display_name='Locust Admin',
                first_name='Locust',
                last_name='Admin'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created load test superuser'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create superuser: {str(e)}'))
            return

        self.stdout.write(self.style.SUCCESS('\nLoad test setup completed successfully!')) 