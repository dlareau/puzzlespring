import os
from .base_settings import *

CUSTOM_CONFIG_DIR = '/app/custom_config'

if os.path.exists(CUSTOM_CONFIG_DIR):
    # Override Django settings
    settings_path = '/app/custom_config/settings.py'
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            exec(f.read()) 