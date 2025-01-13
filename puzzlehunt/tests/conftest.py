import os
import sys
import django
from django.conf import settings

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings.test_settings')
django.setup()
