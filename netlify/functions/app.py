import sys
import os

# Add root project directory to sys.path so app, database, forecast can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import serverless_wsgi
from app import app

def handler(event, context):
    """Netlify serverless function entrypoint for Flask WSGI."""
    return serverless_wsgi.handle_request(app, event, context)
