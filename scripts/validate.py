#!/usr/bin/env python3
"""Portable structural preflight for this plugin (standard library only)."""

import json
from pathlib import Path
import re
import sys

from workflow import config, require


def validate(root):
    manifest = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    require(manifest["name"] == "dev-agent-workflow", "Unexpected plugin name")
    require(root.name == manifest["name"] or (
        root.parent.name == manifest["name"] and root.name == manifest["version"]),
        "Plugin name/folder mismatch (expected source or Codex versioned cache)")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", manifest["version"]), "Invalid version")
    require(manifest["skills"] == "./skills/", "Unexpected skill path")
    require(manifest["author"]["name"] and manifest["description"], "Missing manifest metadata")
    require("hooks" not in manifest, "Unsupported hooks manifest field")
    for field, companion in (("apps", ".app.json"), ("mcpServers", ".mcp.json")):
        require(field not in manifest or (root / companion).is_file(), f"Missing {companion}")
    config(root)
    skills = list((root / "skills").glob("*/SKILL.md"))
    require(bool(skills), "No skills")
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        require(text.startswith("---\n"), "Missing skill frontmatter")
        frontmatter = text.split("---", 2)[1]
        require(f"name: {skill.parent.name}\n" in frontmatter, "Skill name mismatch")
        require("description: " in frontmatter, "Missing skill description")
    for path in [root / ".codex-plugin/plugin.json", *list((root / "skills").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        require("[TODO:" not in text, f"Unfinished scaffold: {path}")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                require((path.parent / target.split("#")[0]).exists(), f"Broken reference: {path}: {target}")
    return {"plugin": manifest["name"], "version": manifest["version"], "skills": len(skills), "result": "pass"}


if __name__ == "__main__":
    try:
        print(json.dumps(validate(Path(__file__).resolve().parents[1]), indent=2))
    except (ValueError, OSError, KeyError, IndexError) as error:
        print(f"validate: {error}", file=sys.stderr)
        sys.exit(1)
