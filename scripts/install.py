#!/usr/bin/env python3
"""Register this checkout in the personal Codex marketplace without replacing entries."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from workflow import require, write_json


def register(source, home):
    source = source.resolve()
    manifest = json.loads((source / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    name = manifest["name"]
    require(name == "dev-agent-workflow" and source.name == name, "Unexpected plugin name or folder")
    registry = home / ".agents/plugins/marketplace.json"
    target = home / "plugins" / name
    entry = {"name": name, "source": {"source": "local", "path": f"./plugins/{name}"},
             "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
             "category": "Productivity"}
    if registry.exists():
        data = json.loads(registry.read_text(encoding="utf-8"))
    else:
        data = {"name": "personal", "interface": {"displayName": "Personal"}, "plugins": []}
    require(isinstance(data, dict), "Invalid personal marketplace")
    market = data.get("name")
    require(isinstance(market, str) and re.fullmatch(r"[A-Za-z0-9_-]+", market),
            "Invalid marketplace name; fix it before installing")
    require(isinstance(data.get("plugins"), list), "Invalid marketplace plugins")
    existing = [p for p in data["plugins"] if isinstance(p, dict) and p.get("name") == name]
    require(len(existing) <= 1, "Duplicate marketplace entries")
    if existing:
        require(existing[0].get("source") == entry["source"],
                "Existing entry points elsewhere; resolve it before installing")
    if target.exists() or target.is_symlink():
        require(target.resolve() == source, "Existing plugin directory points elsewhere; refusing overwrite")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
    if not existing:
        data["plugins"].append(entry)
        write_json(registry, data)
    return {"plugin": name, "marketplace": market, "registry": str(registry), "source": str(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register-only", action="store_true", help="Register source without calling codex plugin add")
    args = parser.parse_args()
    try:
        result = register(Path(__file__).resolve().parents[1], Path.home())
        print(json.dumps(result, indent=2), flush=True)
        if not args.register_only:
            subprocess.run(["codex", "plugin", "add", f"{result['plugin']}@{result['marketplace']}"], check=True)
        print("Start a new Codex session to load the plugin.")
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"install: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
