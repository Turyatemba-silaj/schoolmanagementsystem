import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
os.environ.setdefault('DJANGO_DEBUG', 'False')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
