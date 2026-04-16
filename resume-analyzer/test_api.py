import urllib.request
import json

try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/health')
    data = json.loads(response.read())
    print("Backend health check:", data)

    # Test resumes endpoint
    response = urllib.request.urlopen('http://127.0.0.1:5000/resumes')
    data = json.loads(response.read())
    print("Resumes endpoint:", data)

except Exception as e:
    print("Error:", e)