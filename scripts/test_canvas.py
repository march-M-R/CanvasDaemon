"""Read-only connection check; importing this module never contacts Canvas."""
import os
from canvas_runtime import load_dotenv, requests, validate_config


def main():
    load_dotenv()
    base, token, course = os.getenv("CANVAS_BASE_URL", "").rstrip("/"), os.getenv("CANVAS_TOKEN"), os.getenv("COURSE_ID")
    validate_config(base, token, course)
    response = requests.get(f"{base}/api/v1/courses/{course}", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    data = response.json()
    if str(data["id"]) != course:
        raise ValueError("Unexpected course identity from Canvas.")
    print(f"Connected: {data['name']} (course {data['id']})")


if __name__ == "__main__":
    main()
