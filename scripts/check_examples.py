#!/usr/bin/env python3
"""Check cookbook links and syntax without installing workload dependencies."""

import ast
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "__pycache__", "node_modules", "output", "outputs", "results"}
EXAMPLES = {
    "quickstarts",
    "training",
    "inference",
    "agents",
    "robotics",
    "life-science",
}


def check_file(path: Path) -> None:
    text = path.read_text()
    if path.suffix == ".py":
        ast.parse(text, filename=str(path))
    elif path.suffix == ".sh":
        subprocess.run(["bash", "-n", str(path)], check=True, capture_output=True)
    elif path.suffix == ".json":
        json.loads(text)
    elif path.name == "pyproject.toml":
        tomllib.loads(text)
    elif path.suffix == ".md":
        # Ignore examples of Markdown inside fenced code blocks.
        prose = re.sub(r"^```.*?^```[^\n]*", "", text, flags=re.MULTILINE | re.DOTALL)
        targets = re.findall(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", prose)
        targets += re.findall(r'\b(?:href|src)=["\']([^"\']+)["\']', prose)
        for target in targets:
            target = target.strip("<>")
            url = urlsplit(target)
            if url.scheme or not url.path:
                continue
            destination = path.parent / unquote(url.path)
            if not destination.exists():
                raise ValueError(f"missing linked file: {target}")
        relative = path.relative_to(ROOT)
        is_guide = relative.parts[0] in EXAMPLES and (
            (len(relative.parts) == 3 and path.name == "README.md")
            or (relative.parts[0] == "quickstarts" and len(relative.parts) == 2)
        )
        if is_guide:
            if not text.startswith("---\n"):
                raise ValueError("example needs YAML front matter")
            metadata = text.split("---", 2)[1]
            for field in ("title", "category", "type", "runtime"):
                if not re.search(rf"^{field}:\s*\S", metadata, re.MULTILINE):
                    raise ValueError(f"missing front matter field: {field}")


def main() -> None:
    errors = []
    checked = 0
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or SKIP.intersection(path.relative_to(ROOT).parts):
            continue
        if (
            path.suffix not in {".py", ".sh", ".json", ".md"}
            and path.name != "pyproject.toml"
        ):
            continue
        checked += 1
        try:
            check_file(path)
        except (ValueError, SyntaxError, subprocess.CalledProcessError) as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")
    for error in errors:
        print(error)
    print(f"Checked {checked} files; {len(errors)} errors.")
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
