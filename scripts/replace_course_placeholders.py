import argparse
import json
from pathlib import Path


def apply_values(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
        text = text.replace("[[" + key + "]]", str(value))
    return text


def main():
    parser = argparse.ArgumentParser(description="Replace {{placeholders}} or [[placeholders]] in a file from JSON values.")
    parser.add_argument("input_file")
    parser.add_argument("values_json")
    parser.add_argument("--output")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()
    src = Path(args.input_file)
    values = json.loads(Path(args.values_json).read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("values_json must be an object.")
    rendered = apply_values(src.read_text(encoding="utf-8"), values)
    out = src if args.in_place else Path(args.output) if args.output else src.with_name(src.stem + "__rendered" + src.suffix)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print(f"Wrote: {out}")
    if "{{" in rendered or "[[" in rendered:
        print("Possible unreplaced placeholders remain.")

if __name__ == "__main__":
    main()
