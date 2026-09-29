import argparse
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
INCLUDE = ["README.md", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md", ".env.example", "docs", "examples/templates", "scripts", "tests", "requirements.txt"]

def main():
    parser = argparse.ArgumentParser(description="Export a clean CanvasDaemon toolkit handoff package zip.")
    parser.add_argument("--output", default="reports/exports/canvasdaemon-toolkit.zip")
    args = parser.parse_args()
    out = ROOT_DIR / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in INCLUDE:
            path = ROOT_DIR / rel
            if not path.exists():
                continue
            if path.is_dir():
                for file in path.rglob("*"):
                    if file.is_file() and "__pycache__" not in file.parts:
                        archive.write(file, file.relative_to(ROOT_DIR))
            else:
                archive.write(path, path.relative_to(ROOT_DIR))
    print(f"Wrote clean handoff package: {out}")

if __name__ == "__main__":
    main()
