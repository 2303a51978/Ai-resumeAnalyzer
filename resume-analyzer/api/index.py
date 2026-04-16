import sys
import os
from flask import Flask, jsonify, send_from_directory

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Start with a base app
app = Flask(__name__)

# Try to import the actual backend app
try:
    from backend.app import app as backend_app
    app = backend_app
    print("✓ Successfully loaded backend.app")
except Exception as e:
    print(f"✗ Failed to load backend.app: {e}")

    @app.route('/')
    def index():
        return jsonify({'error': f'Backend import failed: {str(e)}'}), 500

    @app.route('/health')
    def health():
        return jsonify({'status': 'running with fallback app'}), 200

frontend_dir = os.path.join(project_root, 'frontend')

if os.path.isdir(frontend_dir):
    @app.route('/', defaults={'path': 'index.html'})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path.startswith('api/'):
            return jsonify({'error': 'API route not found'}), 404
        full_path = os.path.join(frontend_dir, path)
        if os.path.exists(full_path) and not os.path.isdir(full_path):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, 'index.html')

