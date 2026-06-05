import os
from dotenv import load_dotenv
import requests

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}"

response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)

if response.ok:
    data = response.json()

    print("\nConnected Successfully")
    print("Course Name:", data["name"])
    print("Course ID:", data["id"])
else:
    print(response.text)