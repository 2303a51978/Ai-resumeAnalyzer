import sys
import os

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.app import app
except ImportError as e:
    print(f"Import error: {e}")
    raise

# Vercel serverless function handler
def handler(request):
    return app(request.environ, request.start_response)

# Export app directly for Vercel
__all__ = ['app']
