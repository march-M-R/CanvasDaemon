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

url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/pages"

response = requests.get(
    url,
    headers=headers,
    params={"per_page": 100}
)

print("Status:", response.status_code)

pages = response.json()

print(f"\nFound {len(pages)} pages\n")

for page in pages:
    print(
        f"Title: {page['title']}\n"
        f"URL: {page['url']}\n"
    )