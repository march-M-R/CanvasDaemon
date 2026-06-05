import os
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("CANVAS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")

ROOT_DIR = Path(__file__).resolve().parents[1]

ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
QUIZ_REPORTS_DIR = ROOT_DIR / "reports" / "quizzes"
CLASSIC_QUIZZES_CSV = QUIZ_REPORTS_DIR / "classic_quizzes.csv"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


def check_env():
    if not BASE_URL or not TOKEN or not COURSE_ID:
        raise RuntimeError(
            "Missing .env values. Required: CANVAS_BASE_URL, CANVAS_TOKEN, COURSE_ID"
        )


def load_quiz_bank(path):
    quiz_path = Path(path)

    if not quiz_path.exists():
        raise FileNotFoundError(f"Quiz bank not found: {quiz_path}")

    return json.loads(quiz_path.read_text(encoding="utf-8"))


def load_asset_manifest():
    if not ASSET_MANIFEST_PATH.exists():
        return {"files": {}}

    return json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))


def find_asset_url(asset_name_or_id):
    """
    Resolves an image reference from asset_manifest.json.

    Supported:
    - "canvasdaemon_test_image.png"
    - "16255"
    - 16255
    """
    if not asset_name_or_id:
        return None

    manifest = load_asset_manifest()
    files = manifest.get("files", {})

    lookup = str(asset_name_or_id).strip().lower()

    if lookup in files:
        return files[lookup].get("url")

    matches = []

    for file_id, info in files.items():
        filename = (info.get("filename") or "").lower()
        display_name = (info.get("display_name") or "").lower()

        if lookup == filename or lookup == display_name:
            matches.append(info)

    if len(matches) == 1:
        return matches[0].get("url")

    if len(matches) > 1:
        raise ValueError(
            f'Multiple assets matched "{asset_name_or_id}". '
            "Use the Canvas file ID instead."
        )

    raise ValueError(
        f'Asset not found in asset_manifest.json: "{asset_name_or_id}".\n'
        "Run: python scripts/pull_files_metadata.py\n"
        "Then try: python scripts/find_asset.py \"your_asset_name\""
    )


def image_html(asset_name_or_id, alt_text):
    url = find_asset_url(asset_name_or_id)
    return (
        f'<p>'
        f'<img src="{url}" alt="{alt_text}" '
        f'style="max-width: 100%; height: auto;">'
        f'</p>'
    )


def build_question_text(question):
    parts = []

    if question.get("image"):
        parts.append(
            image_html(
                asset_name_or_id=question["image"],
                alt_text=question.get("image_alt", question.get("question_name", "Quiz image"))
            )
        )

    metadata_bits = []

    if question.get("objective"):
        metadata_bits.append(f"<strong>Objective:</strong> {question['objective']}")

    if question.get("difficulty"):
        metadata_bits.append(f"<strong>Difficulty:</strong> {question['difficulty']}")

    if question.get("tags"):
        tags = ", ".join(question["tags"])
        metadata_bits.append(f"<strong>Tags:</strong> {tags}")

    if metadata_bits:
        parts.append(
            '<div style="font-size: 0.9em; color: #555; margin-bottom: 12px;">'
            + "<br>".join(metadata_bits)
            + "</div>"
        )

    parts.append(f"<p>{question['question_text']}</p>")

    return "\n".join(parts)


def create_quiz(quiz_bank):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes"

    payload = {
        "quiz[title]": quiz_bank["title"],
        "quiz[description]": quiz_bank.get("description", ""),
        "quiz[quiz_type]": quiz_bank.get("quiz_type", "assignment"),
        "quiz[published]": str(quiz_bank.get("published", False)).lower(),
        "quiz[shuffle_answers]": str(quiz_bank.get("shuffle_answers", True)).lower(),
        "quiz[allowed_attempts]": quiz_bank.get("allowed_attempts", 1),
        "quiz[scoring_policy]": quiz_bank.get("scoring_policy", "keep_highest"),
    }

    if quiz_bank.get("time_limit") is not None:
        payload["quiz[time_limit]"] = quiz_bank["time_limit"]

    if quiz_bank.get("show_correct_answers") is not None:
        payload["quiz[show_correct_answers]"] = str(
            quiz_bank.get("show_correct_answers")
        ).lower()

    if "hide_results" in quiz_bank:
        payload["quiz[hide_results]"] = quiz_bank["hide_results"]

    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def build_answers_for_multiple_choice(question):
    return [
        {
            "text": choice["text"],
            "weight": 100 if choice.get("correct") else 0
        }
        for choice in question["choices"]
    ]


def build_answers_for_true_false(question):
    correct = bool(question["correct"])

    return [
        {
            "text": "True",
            "weight": 100 if correct else 0
        },
        {
            "text": "False",
            "weight": 0 if correct else 100
        }
    ]


def build_answers_for_multiple_answers(question):
    return [
        {
            "text": choice["text"],
            "weight": 100 if choice.get("correct") else 0
        }
        for choice in question["choices"]
    ]


def build_answers_for_fill_blank(question):
    return [
        {
            "text": answer,
            "weight": 100
        }
        for answer in question["answers"]
    ]


def build_canvas_question(question):
    qtype = question["type"]

    if qtype == "multiple_choice":
        canvas_type = "multiple_choice_question"
        answers = build_answers_for_multiple_choice(question)

    elif qtype == "true_false":
        canvas_type = "true_false_question"
        answers = build_answers_for_true_false(question)

    elif qtype == "multiple_answers":
        canvas_type = "multiple_answers_question"
        answers = build_answers_for_multiple_answers(question)

    elif qtype == "fill_blank":
        canvas_type = "short_answer_question"
        answers = build_answers_for_fill_blank(question)

    else:
        raise ValueError(f"Unsupported question type: {qtype}")

    canvas_question = {
        "question_name": question.get("question_name", question["question_text"][:40]),
        "question_text": build_question_text(question),
        "question_type": canvas_type,
        "points_possible": question.get("points_possible", 1),
        "answers": answers
    }

    if question.get("correct_comments"):
        canvas_question["correct_comments"] = question["correct_comments"]

    if question.get("incorrect_comments"):
        canvas_question["incorrect_comments"] = question["incorrect_comments"]

    if question.get("neutral_comments"):
        canvas_question["neutral_comments"] = question["neutral_comments"]

    return canvas_question


def add_question(quiz_id, question):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes/{quiz_id}/questions"

    payload = {
        "question": build_canvas_question(question)
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


def append_quiz_report(quiz, quiz_bank_path, quiz_bank, question_count):
    QUIZ_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = CLASSIC_QUIZZES_CSV.exists()

    with CLASSIC_QUIZZES_CSV.open("a", newline="", encoding="utf-8") as f:
        fieldnames = [
            "created_at",
            "quiz_id",
            "title",
            "module",
            "lesson",
            "published",
            "html_url",
            "question_count",
            "source_json"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "quiz_id": quiz.get("id"),
            "title": quiz.get("title"),
            "module": quiz_bank.get("module"),
            "lesson": quiz_bank.get("lesson"),
            "published": quiz.get("published"),
            "html_url": quiz.get("html_url"),
            "question_count": question_count,
            "source_json": str(quiz_bank_path)
        })


def main():
    check_env()

    parser = argparse.ArgumentParser(
        description="Create an unpublished Classic Canvas Quiz from JSON."
    )
    parser.add_argument("quiz_json", help="Path to quiz bank JSON file")
    args = parser.parse_args()

    quiz_bank = load_quiz_bank(args.quiz_json)

    quiz = create_quiz(quiz_bank)
    quiz_id = quiz["id"]

    print("\nCreated Classic Quiz")
    print("=" * 80)
    print(f"Title: {quiz.get('title')}")
    print(f"Quiz ID: {quiz_id}")
    print(f"Published: {quiz.get('published')}")
    print(f"URL: {quiz.get('html_url')}")
    print("=" * 80)

    questions = quiz_bank.get("questions", [])

    for index, question in enumerate(questions, start=1):
        created_question = add_question(quiz_id, question)
        print(f"[{index}/{len(questions)}] Added question: {created_question.get('question_name')}")

    append_quiz_report(
        quiz=quiz,
        quiz_bank_path=args.quiz_json,
        quiz_bank=quiz_bank,
        question_count=len(questions)
    )

    print("\nDone.")
    print(f"Questions added: {len(questions)}")
    print(f"Report updated: {CLASSIC_QUIZZES_CSV}")
    print("\nNext: open the quiz in Canvas and verify it before publishing.")


if __name__ == "__main__":
    main()