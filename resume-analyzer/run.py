#!/usr/bin/env python3
"""
Resume Analyzer - Start Script
Starts both backend and frontend servers
"""

import subprocess
import sys
import os
import time
import signal
import threading

def setup_environment():
    """Install dependencies and setup database"""
    print("Setting up environment...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    # Install requirements
    print("Installing Python dependencies...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to install dependencies: {result.stderr}")
        return False
    
    # Create database tables
    print("Setting up database...")
    result = subprocess.run([sys.executable, '-c', 'from app import create_tables; create_tables()'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to setup database: {result.stderr}")
        return False
    
    print("Environment setup complete!")
    return True

def start_backend():
    """Start the Flask backend server"""
    print("Starting backend server...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    return subprocess.Popen([sys.executable, 'app.py'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)

def start_frontend():
    """Start the frontend server"""
    print("Frontend is now served by the Flask backend - no separate server needed")
    return None
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    os.chdir(frontend_dir)
    # Use Python's built-in HTTP server
    return subprocess.Popen([sys.executable, '-m', 'http.server', '8000'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)

def main():
    print("Resume Analyzer - Starting server...")
    print("=" * 50)
    
    # Setup environment first
    if not setup_environment():
        print("Failed to setup environment. Exiting.")
        sys.exit(1)
    
    # Start backend (which now serves both backend API and frontend)
    backend_process = start_backend()
    time.sleep(2)  # Wait for backend to start
    
    print("\n" + "=" * 50)
    print("Server started successfully!")
    print("Application: http://127.0.0.1:5000")
    print("Login at: http://127.0.0.1:5000/login")
    print("=" * 50)
    print("Press Ctrl+C to stop server")
    
    try:
        # Wait for backend to finish
        backend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        print("Servers stopped.")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Press Ctrl+C to stop server")

if __name__ == '__main__':
    main()