import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# Load settings from Django settings.py file using CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks inside all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
