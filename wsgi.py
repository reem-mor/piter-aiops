"""Gunicorn entry point: `gunicorn -b 0.0.0.0:8080 wsgi:app`."""
from app import create_app

app = create_app()
