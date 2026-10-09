"""Build a portable static site. All paths work below a GitHub project prefix."""
import argparse
import json
from pathlib import Path
import shutil


def build(data_dir, output):
    data_dir, output = Path(data_dir), Path(output)
    payload = json.loads((data_dir / "index.json").read_text())
    if payload.get("schema_version") not in (1, 2):
        raise ValueError("Unsupported archive schema")
    if payload.get("schema_version") == 2:
        from topics_schema import validate_archive
        validate_archive(payload)
    output.mkdir(parents=True, exist_ok=True)
    static = Path(__file__).parent / "static"
    for path in static.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)
    shutil.copytree(data_dir, output / "data", dirs_exist_ok=True)
    (output / ".nojekyll").touch()
    print(f"Built {len(payload['items'])} items to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="_site")
    args = parser.parse_args()
    build(args.data_dir, args.output)
