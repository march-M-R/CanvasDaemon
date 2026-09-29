import os
import csv
from pathlib import Path

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]
QUIZ_REPORTS_DIR = ROOT_DIR / "reports" / "quizzes"
CLASSIC_QUIZZES_CSV = QUIZ_REPORTS_DIR / "classic_quizzes_inventory.csv"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def canvas_get_all(url, params=None):
    results = []

    seen_urls = set()
    while url:
        if url in seen_urls:
            raise RuntimeError("Canvas repeated a pagination URL.")
        seen_urls.add(url)
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()

        results.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None

    return results


def get_classic_quizzes():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes"
    return canvas_get_all(url, params={"per_page": 100})


def main():
    check_env()
    QUIZ_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    quizzes = get_classic_quizzes()

    rows = []

    for quiz in quizzes:
        rows.append({
            "quiz_id": quiz.get("id"),
            "title": quiz.get("title"),
            "published": quiz.get("published"),
            "quiz_type": quiz.get("quiz_type"),
            "points_possible": quiz.get("points_possible"),
            "question_count": quiz.get("question_count"),
            "time_limit": quiz.get("time_limit"),
            "allowed_attempts": quiz.get("allowed_attempts"),
            "shuffle_answers": quiz.get("shuffle_answers"),
            "show_correct_answers": quiz.get("show_correct_answers"),
            "html_url": quiz.get("html_url"),
            "created_at": quiz.get("created_at"),
            "updated_at": quiz.get("updated_at")
        })

    with CLASSIC_QUIZZES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "quiz_id",
                "title",
                "published",
                "quiz_type",
                "points_possible",
                "question_count",
                "time_limit",
                "allowed_attempts",
                "shuffle_answers",
                "show_correct_answers",
                "html_url",
                "created_at",
                "updated_at"
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    print("Classic quiz inventory complete.")
    print(f"Quizzes found: {len(rows)}")
    print(f"Report saved to: {CLASSIC_QUIZZES_CSV}")


if __name__ == "__main__":
    main()
