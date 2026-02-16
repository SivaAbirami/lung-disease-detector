import os
import sys
import traceback

# Add the project directory to sys.path (mimic manage.py)
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

print("Attempting to import backend.wsgi...")
try:
    from backend import wsgi
    print(f"WSGI module imported: {wsgi}")
    print(f"Application object: {wsgi.application}")
    print("Success!")
except Exception:
    traceback.print_exc()
