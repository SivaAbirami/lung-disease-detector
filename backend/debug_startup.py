import os
import sys
import django
from django.conf import settings

# Add the project directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

print("Attempting to import settings...")
try:
    from backend import settings as app_settings
    print(f"Settings imported successfully: {app_settings}")
except Exception as e:
    print(f"Failed to import settings: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to populate apps...")
try:
    django.setup()
    print("Django setup successful.")
except Exception as e:
    print(f"Django setup failed: {e}")
    import traceback
    traceback.print_exc()
