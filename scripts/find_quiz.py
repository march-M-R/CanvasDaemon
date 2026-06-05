import csv
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
QUIZZES_CSV = ROOT_DIR / "reports" / "quizzes" / "classic_quizzes_inventory.csv"


def normalize(text):
    return (text or "").lower().strip()


def load_quizzes():
    if not QUIZZES_CSV.exists():
        raise FileNotFoundError(
            "reports/quizzes/classic_quizzes_inventory.csv not found.\n"
            "Run: python scripts/pull_classic_quizzes.py"
        )

    with QUIZZES_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/find_quiz.py "search text"')
        sys.exit(1)

    search_text = normalize(" ".join(sys.argv[1:]))
    quizzes = load_quizzes()

    matches = []

    for quiz in quizzes:
        haystack = " ".join([
            quiz.get("quiz_id", ""),
            quiz.get("title", ""),
            quiz.get("published", ""),
            quiz.get("quiz_type", ""),
            quiz.get("html_url", "")
        ])

        if search_text in normalize(haystack):
            matches.append(quiz)

    if not matches:
        print(f'No quizzes found for: "{search_text}"')
        print("\nTry:")
        print('python scripts/find_quiz.py "test"')
        print('python scripts/find_quiz.py "module"')
        print('python scripts/find_quiz.py "false"')
        return

    print(f'\nFound {len(matches)} quiz match(es) for: "{search_text}"\n')

    for i, quiz in enumerate(matches, start=1):
        print("=" * 80)
        print(f"{i}. Title:             {quiz.get('title')}")
        print(f"   Quiz ID:           {quiz.get('quiz_id')}")
        print(f"   Published:         {quiz.get('published')}")
        print(f"   Quiz type:         {quiz.get('quiz_type')}")
        print(f"   Points:            {quiz.get('points_possible')}")
        print(f"   Questions:         {quiz.get('question_count')}")
        print(f"   Time limit:        {quiz.get('time_limit')}")
        print(f"   Allowed attempts:  {quiz.get('allowed_attempts')}")
        print(f"   Shuffle answers:   {quiz.get('shuffle_answers')}")
        print(f"   Show answers:      {quiz.get('show_correct_answers')}")
        print(f"   Updated at:        {quiz.get('updated_at')}")
        print(f"   URL:               {quiz.get('html_url')}")
        print()
        print(f'   Update settings dry-run later:')
        print(f'   python scripts/sync_classic_quiz.py "quiz_banks/test_classic_quiz.json"')
        print()


if __name__ == "__main__":
    main()