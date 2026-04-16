import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app import app

# Export the app for Vercel
if __name__ == "__main__":
    app.run(debug=False)
