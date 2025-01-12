from django.core.management.commands.flush import Command as FlushCommand
from django.core.management import call_command

class Command(FlushCommand):
    def handle(self, *args, **options):
        # Run the parent flush command first
        super().handle(*args, **options)
        
        # Then ensure groups are recreated
        self.stdout.write('Recreating groups and permissions...')
        call_command('ensure_groups')