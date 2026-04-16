import sys
import os

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Flask app with error handling
try:
    from backend.app import app
except ImportError as e:
    import traceback
    error_msg = f"Failed to import backend.app: {str(e)}\n{traceback.format_exc()}"
    print(f"[ERROR] {error_msg}")
    
    # Create a minimal Flask app to show error
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error_handler():
        return {'error': error_msg}, 500

# Verify app is a Flask instance
if not hasattr(app, '__call__'):
    raise RuntimeError("app must be a WSGI application")
