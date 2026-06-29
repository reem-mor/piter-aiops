"""Course guideline entry point alias.

The production entry point is ``wsgi:app`` (Gunicorn). This module exists so
submissions match the guideline's ``app.py`` expectation without duplicating logic.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
