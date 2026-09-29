from canvas_runtime import add_write_flags, authorize
import os
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime

from canvas_runtime import requests
from canvas_runtime import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]

QUIZ_REPORTS_DIR = ROOT_DIR / "reports" / "quizzes"
QUIZZES_INVENTORY_CSV = QUIZ_REPORTS_DIR / "classic_quizzes_inventory.csv"
SYNC_REPORT_CSV = QUIZ_REPORTS_DIR / "classic_quiz_sync_log.csv"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    from canvas_runtime import validate_config
    validate_config(BASE_URL, TOKEN, COURSE_ID)


def load_quiz_bank(path):
    quiz_path = Path(path)

    if not quiz_path.exists():
        raise FileNotFoundError(f"Quiz bank not found: {quiz_path}")

    return json.loads(quiz_path.read_text(encoding="utf-8"))


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


def find_quiz_by_title(title):
    quizzes = get_classic_quizzes()

    matches = [
        quiz for quiz in quizzes
        if (quiz.get("title") or "").strip() == title.strip()
    ]

    return matches


def build_quiz_payload(quiz_bank):
    payload = {
        "quiz[title]": quiz_bank["title"],
        "quiz[description]": quiz_bank.get("description", ""),
        "quiz[quiz_type]": quiz_bank.get("quiz_type", "assignment"),
        "quiz[shuffle_answers]": str(quiz_bank.get("shuffle_answers", True)).lower(),
        "quiz[allowed_attempts]": quiz_bank.get("allowed_attempts", 1),
        "quiz[scoring_policy]": quiz_bank.get("scoring_policy", "keep_highest"),
    }

    if "published" in quiz_bank:
        if not isinstance(quiz_bank["published"], bool):
            raise ValueError("published must be a JSON boolean.")
        payload["quiz[published]"] = str(quiz_bank["published"]).lower()

    if quiz_bank.get("time_limit") is not None:
        payload["quiz[time_limit]"] = quiz_bank["time_limit"]

    if quiz_bank.get("show_correct_answers") is not None:
        payload["quiz[show_correct_answers]"] = str(
            quiz_bank.get("show_correct_answers")
        ).lower()

    if "hide_results" in quiz_bank:
        payload["quiz[hide_results]"] = quiz_bank["hide_results"]

    return payload


def create_quiz(quiz_bank):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes"
    response = requests.post(url, headers=HEADERS, data={**build_quiz_payload(quiz_bank), "quiz[published]": "false"})
    response.raise_for_status()
    return response.json()


def update_quiz(quiz_id, quiz_bank):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes/{quiz_id}"
    response = requests.put(url, headers=HEADERS, data=build_quiz_payload(quiz_bank))
    response.raise_for_status()
    return response.json()


def append_sync_log(action, quiz_id, title, source_json, applied):
    QUIZ_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = SYNC_REPORT_CSV.exists()

    with SYNC_REPORT_CSV.open("a", newline="", encoding="utf-8") as f:
        fieldnames = [
            "timestamp",
            "action",
            "quiz_id",
            "title",
            "source_json",
            "applied"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "quiz_id": quiz_id,
            "title": title,
            "source_json": source_json,
            "applied": applied
        })


def print_planned_payload(quiz_bank):
    print("\nPlanned quiz settings:")
    print("=" * 80)
    print(f"Title:                {quiz_bank.get('title')}")
    print(f"Description:          {quiz_bank.get('description')}")
    print(f"Published:            {quiz_bank.get('published', False)}")
    print(f"Time limit:           {quiz_bank.get('time_limit')}")
    print(f"Allowed attempts:     {quiz_bank.get('allowed_attempts', 1)}")
    print(f"Shuffle answers:      {quiz_bank.get('shuffle_answers', True)}")
    print(f"Show correct answers: {quiz_bank.get('show_correct_answers')}")
    print(f"Questions in JSON:    {len(quiz_bank.get('questions', []))}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Classic Canvas Quiz settings from JSON. Dry-run by default."
    )

    parser.add_argument(
        "quiz_json",
        help="Path to quiz bank JSON file"
    )

    add_write_flags(parser)
    args = parser.parse_args()
    check_env()
    if args.apply:
        authorize(args, BASE_URL, COURSE_ID)

    quiz_bank = load_quiz_bank(args.quiz_json)
    title = quiz_bank["title"]

    matches = find_quiz_by_title(title)

    print_planned_payload(quiz_bank)

    if len(matches) > 1:
        print(f'\nMultiple quizzes found with exact title: "{title}"')
        print("Refusing to sync because this is ambiguous.")
        print("\nMatches:")
        for quiz in matches:
            print(f"- Quiz ID {quiz.get('id')}: {quiz.get('html_url')}")
        return

    if len(matches) == 0:
        print(f'\nNo existing quiz found with title: "{title}"')
        print("Planned action: CREATE NEW QUIZ")

        if not args.apply:
            print("\nDRY RUN ONLY. Nothing was created.")
            print("To apply:")
            print(f'python scripts/sync_classic_quiz.py "{args.quiz_json}" --apply --confirm-course {COURSE_ID}')
            append_sync_log(
                action="dry_run_create",
                quiz_id="",
                title=title,
                source_json=args.quiz_json,
                applied=False
            )
            return

        created = create_quiz(quiz_bank)

        print("\nCreated quiz successfully.")
        print(f"Quiz ID: {created.get('id')}")
        print(f"URL: {created.get('html_url')}")

        append_sync_log(
            action="create",
            quiz_id=created.get("id"),
            title=title,
            source_json=args.quiz_json,
            applied=True
        )
        return

    quiz = matches[0]
    quiz_id = quiz["id"]

    print(f'\nExisting quiz found: "{title}"')
    print(f"Quiz ID: {quiz_id}")
    print(f"URL: {quiz.get('html_url')}")
    print("Planned action: UPDATE QUIZ SETTINGS ONLY")

    if not args.apply:
        print("\nDRY RUN ONLY. Nothing was updated.")
        print("To apply:")
        print(f'python scripts/sync_classic_quiz.py "{args.quiz_json}" --apply --confirm-course {COURSE_ID}')

        append_sync_log(
            action="dry_run_update_settings",
            quiz_id=quiz_id,
            title=title,
            source_json=args.quiz_json,
            applied=False
        )
        return

    from canvas_runtime import save_json
    save_json(ROOT_DIR / "backups" / ("quiz-settings-" + str(quiz_id) + "-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".json"), quiz)
    updated = update_quiz(quiz_id, quiz_bank)

    print("\nUpdated quiz settings successfully.")
    print(f"Quiz ID: {updated.get('id')}")
    print(f"URL: {updated.get('html_url')}")

    append_sync_log(
        action="update_settings",
        quiz_id=quiz_id,
        title=title,
        source_json=args.quiz_json,
        applied=True
    )


if __name__ == "__main__":
    main()
