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

ASSET_MANIFEST_PATH = ROOT_DIR / "asset_manifest.json"
QUIZ_REPORTS_DIR = ROOT_DIR / "reports" / "quizzes"
CLASSIC_QUIZZES_CSV = QUIZ_REPORTS_DIR / "classic_quizzes.csv"

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

    # Objective, difficulty, and tags are authoring metadata. They must not be
    # rendered in the student-facing prompt because they can reveal the skill or
    # terminology the question is asking students to identify.

    question_text = question["question_text"]
    # Some quiz questions contain real code blocks. Avoid placing block-level
    # HTML inside a paragraph because Canvas may flatten or repair it badly.
    if any(tag in question_text.lower() for tag in ("<pre", "<div", "<table", "<p")):
        parts.append(question_text)
    else:
        parts.append(f"<p>{question_text}</p>")

    return "\n".join(parts)


def create_quiz(quiz_bank):
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/quizzes"

    payload = {
        "quiz[title]": quiz_bank["title"],
        "quiz[description]": quiz_bank.get("description", ""),
        "quiz[quiz_type]": quiz_bank.get("quiz_type", "assignment"),
        "quiz[published]": "false",
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
    if not response.ok:
        raise RuntimeError(
            f"Canvas quiz creation failed (HTTP {response.status_code})."
        )
    return response.json()


def build_answers_for_multiple_choice(question):
    choices = question.get("choices", question.get("answers", []))
    return [
        {
            "text": choice["text"],
            "weight": 100 if choice.get("correct") else 0
        }
        for choice in choices
    ]


def build_answers_for_true_false(question):
    if not isinstance(question.get("correct"), bool):
        raise ValueError("true_false correct must be a JSON boolean.")
    correct = question["correct"]

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
    choices = question.get("choices", question.get("answers", []))
    return [
        {
            "text": choice["text"],
            "weight": 100 if choice.get("correct") else 0
        }
        for choice in choices
    ]


def build_answers_for_fill_blank(question):
    return [
        {
            "text": answer,
            "weight": 100
        }
        for answer in question["answers"]
    ]


def build_answers_for_likert_5(question):
    labels = question.get(
        "labels",
        [
            "1 — Strongly disagree / very poor",
            "2 — Disagree / needs work",
            "3 — Neutral / okay",
            "4 — Agree / good",
            "5 — Strongly agree / excellent",
        ],
    )
    if len(labels) != 5:
        raise ValueError("likert_5 questions must provide exactly five labels")
    return [{"text": label, "weight": 0} for label in labels]


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

    elif qtype == "essay":
        canvas_type = "essay_question"
        answers = []

    elif qtype == "likert_5":
        canvas_type = "multiple_choice_question"
        answers = build_answers_for_likert_5(question)

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
    if not response.ok:
        raise RuntimeError(
            f"Canvas question creation failed (HTTP {response.status_code})."
        )
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


def validate_quiz_bank(bank):
    if not isinstance(bank.get("title"), str) or not bank["title"].strip():
        raise ValueError("Quiz requires a title.")
    if not isinstance(bank.get("questions"), list) or not bank["questions"]:
        raise ValueError("Quiz requires at least one question.")
    for question in bank["questions"]:
        if not isinstance(question.get("question_text"), str) or not question["question_text"].strip():
            raise ValueError("Each question requires question_text.")
        points = question.get("points_possible", 1)
        if isinstance(points, bool) or not isinstance(points, (int, float)) or points < 0:
            raise ValueError("Question points must be nonnegative numbers.")
        kind = question.get("type")
        if kind in ("multiple_choice", "multiple_answers"):
            choices = question.get("choices", question.get("answers", []))
            if (len(choices) < 2 or any(not isinstance(c.get("text"), str) or not c["text"].strip()
                    or not isinstance(c.get("correct"), bool) for c in choices)):
                raise ValueError("Choices need text and a JSON boolean correct flag.")
            count = sum(c["correct"] for c in choices)
            if (kind == "multiple_choice" and count != 1) or (kind == "multiple_answers" and count < 1):
                raise ValueError("Invalid number of correct answers.")
        if kind == "fill_blank" and (not question.get("answers") or any(not isinstance(a, str) or not a.strip() for a in question["answers"])):
            raise ValueError("fill_blank needs nonempty accepted answer strings.")
        if kind == "likert_5" and points != 0:
            raise ValueError("likert_5 is a survey item and must use points_possible: 0.")
        build_canvas_question(question)  # Validate every type and referenced asset before creating the quiz.


def main():
    parser = argparse.ArgumentParser(
        description="Create an unpublished Classic Canvas Quiz from JSON."
    )
    parser.add_argument("quiz_json", help="Path to quiz bank JSON file")
    add_write_flags(parser)
    args = parser.parse_args()
    check_env()

    quiz_bank = load_quiz_bank(args.quiz_json)
    validate_quiz_bank(quiz_bank)
    print(f"Plan: create unpublished quiz {quiz_bank['title']!r} with {len(quiz_bank['questions'])} questions.")

    if not authorize(args, BASE_URL, COURSE_ID):
        return

    quiz = create_quiz(quiz_bank)
    quiz_id = quiz["id"]
    from canvas_runtime import save_json
    save_json(QUIZ_REPORTS_DIR / f"created-{quiz_id}.json", {"quiz": quiz, "source": args.quiz_json, "status": "questions-pending"})

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

    save_json(QUIZ_REPORTS_DIR / f"created-{quiz_id}.json", {"quiz": quiz, "source": args.quiz_json, "status": "complete", "question_count": len(questions)})
    print("\nDone.")
    print(f"Questions added: {len(questions)}")
    print(f"Report updated: {CLASSIC_QUIZZES_CSV}")
    print("\nNext: open the quiz in Canvas and verify it before publishing.")


if __name__ == "__main__":
    main()
