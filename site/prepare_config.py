"""Drop SMTP settings from the existing custom config without logging it."""
import os
from pathlib import Path
import yaml

config = yaml.safe_load(os.environ["CUSTOM_CONFIG"])
if not isinstance(config, dict):
    raise ValueError("CUSTOM_CONFIG must be a YAML mapping")
config.pop("email", None)
Path("config/custom.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
print("Prepared upstream config without SMTP settings")
