"""Build a portable static site. All paths work below a GitHub project prefix."""
import argparse
import json
from pathlib import Path
import shutil


def build(data_dir, output, static_dir=None):
    data_dir, output = Path(data_dir), Path(output)
    payload = json.loads((data_dir / "index.json").read_text())
    if payload.get("schema_version") not in (1, 2):
        raise ValueError("Unsupported archive schema")
    from topics_schema import validate_archive
    from topics_public import complete_public_topics
    complete_public_topics(payload)
    validate_archive(payload)
    static = Path(static_dir) if static_dir else Path(__file__).parent / "static"
    support_path=static / "schema-support.json"
    supported=json.loads(support_path.read_text()).get("archive_schema_versions",[]) if support_path.exists() else [1]
    if payload["schema_version"] not in supported:
        raise ValueError("Frontend does not support this archive schema")
    output.mkdir(parents=True, exist_ok=True)
    for path in static.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)
    # The candidate cache contains excluded discovery metadata, not reading content.
    shutil.copytree(data_dir, output / "data", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("journal-state.json"))
    (output / "data" / "journal-state.json").unlink(missing_ok=True)
    def write_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")

    index = output / "data" / "index.json"
    write_json(index, payload)
    # Build also upgrades historical full snapshots; daily ID manifests stay intact.
    for snapshot in (output / "data").rglob("*.json"):
        if snapshot == index:
            continue
        try:
            archive = json.loads(snapshot.read_text())
        except (ValueError, OSError):
            continue
        if isinstance(archive, dict) and archive.get("schema_version") in (1, 2) and isinstance(archive.get("items"), list):
            complete_public_topics(archive)
            validate_archive(archive)
            write_json(snapshot, archive)
    write_json(output / "data" / "source-health.json", {
        "generated_at": payload.get("generated_at"),
        "sources": [{key: source[key] for key in ("id", "status", "last_attempt") if key in source}
                    for source in payload.get("sources", [])],
    })
    if (static / "landscape.html").is_file():
        from landscape import write_landscape
        write_landscape(payload, output)
    (output / ".nojekyll").touch()
    print(f"Built {len(payload['items'])} items to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="_site")
    parser.add_argument("--static-dir")
    args = parser.parse_args()
    build(args.data_dir, args.output, args.static_dir)
