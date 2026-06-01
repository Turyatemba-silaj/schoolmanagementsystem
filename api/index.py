import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
os.environ.setdefault('DJANGO_DEBUG', 'False')

if os.environ.get('VERCEL') and not os.environ.get('DJANGO_SUPERUSER_PASSWORD'):
    os.environ.setdefault('DJANGO_SUPERUSER_USERNAME', 'admin')
    os.environ.setdefault('DJANGO_SUPERUSER_PASSWORD', 'admin123')
    os.environ.setdefault('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')

from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

app = get_wsgi_application()

if os.environ.get('VERCEL_AUTO_MIGRATE', 'True') == 'True':
    call_command('migrate', interactive=False, verbosity=0)
    call_command('bootstrap_admin', verbosity=0)
