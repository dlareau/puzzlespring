import os
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Load converted data into the database'

    def add_arguments(self, parser):
        parser.add_argument('converted_data_dir', type=str, help='Directory containing the converted data')

    def handle(self, *args, **options):
        converted_data_dir = options['converted_data_dir']
        media_dir = settings.MEDIA_ROOT

        # Warn the user
        self.stdout.write(self.style.WARNING('This command will erase existing data. Do you want to continue? (yes/no)'))
        confirm = input().strip().lower()
        if confirm != 'yes':
            self.stdout.write(self.style.ERROR('Operation cancelled.'))
            return

        # Clear the existing trusted media folder
        old_trusted_media_dir = os.path.join(media_dir, 'trusted')
        if os.path.exists(old_trusted_media_dir):
            shutil.rmtree(old_trusted_media_dir)
            self.stdout.write(self.style.SUCCESS('Cleared existing trusted media folder.'))

        # Copy the converted data into the media folder
        new_trusted_media_dir = os.path.join(converted_data_dir, 'media', 'trusted')
        shutil.copytree(new_trusted_media_dir, old_trusted_media_dir)
        self.stdout.write(self.style.SUCCESS('Copied converted data into the media folder.'))

        # Flush the database
        call_command('flush', '--no-input')
        self.stdout.write(self.style.SUCCESS('Database flushed.'))

        # Load the converted data into the database using loaddata
        converted_data_file = os.path.join(converted_data_dir, 'converted_data.json')
        call_command('loaddata', converted_data_file)
        self.stdout.write(self.style.SUCCESS('Loaded converted data into the database.')) 