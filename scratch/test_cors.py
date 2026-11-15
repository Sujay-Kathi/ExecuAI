import requests

url = "http://localhost:8000/api/chat"
headers = {
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
}

print(f"Testing OPTIONS {url}...")
try:
    response = requests.options(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}")

url_slash = "http://localhost:8000/api/chat/"
print(f"\nTesting OPTIONS {url_slash}...")
try:
    response = requests.options(url_slash, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}")
