from django.core.management.base import BaseCommand
import subprocess
import signal
import sys

class Command(BaseCommand):
    help = 'Runs development server and huey worker together'

    def handle(self, *args, **options):
        django = subprocess.Popen(['python', 'manage.py', 'runserver'])
        huey = subprocess.Popen(['python', 'manage.py', 'run_huey'])
        
        try:
            django.wait()
        except KeyboardInterrupt:
            django.terminate()
            huey.terminate()
            django.wait()
            huey.wait()
            sys.exit(0)