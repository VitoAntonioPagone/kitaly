#!/usr/bin/env python3
"""Fail if obvious Italian UI literals are present in owner/admin templates."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN_TEMPLATES = ROOT / "templates" / "admin"

# Targeted terms that should not appear as owner-facing UI literals.
FORBIDDEN = [
    r"\bpanoramica\b",
    r"\bcampionato\b",
    r"\bnazionali\b",
    r"\baccessorio\b",
    r"\bannulla\b",
    r"\bsalva\b",
    r"\bmodifica\b",
    r"\belimina\b",
    r"\bconferma\b",
    r"\berrore\b",
    r"\bsuccesso\b",
    r"\bchiudi\b",
    r"\bindietro\b",
    r"\bdisponibil(?:ita|ità)\b",
    r"\bpreordine\b",
]

PATTERN = re.compile("|".join(FORBIDDEN), re.IGNORECASE)
JINJA_BLOCK = re.compile(r"{%.*?%}|{{.*?}}|{#.*?#}", re.DOTALL)
TEXT_NODE = re.compile(r">([^<]+)<")
SCRIPT_STYLE_BLOCK = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def extract_text_candidates(raw: str) -> list[str]:
    stripped = SCRIPT_STYLE_BLOCK.sub("", raw)
    stripped = JINJA_BLOCK.sub("", stripped)
    nodes = [re.sub(r"\s+", " ", m.group(1)).strip() for m in TEXT_NODE.finditer(stripped)]
    return [n for n in nodes if n]


def main() -> int:
    issues: list[tuple[Path, str]] = []
    for file_path in sorted(ADMIN_TEMPLATES.glob("*.html")):
        content = file_path.read_text(encoding="utf-8")
        for node in extract_text_candidates(content):
            if PATTERN.search(node):
                issues.append((file_path, node))

    if issues:
        print("Owner English-only check failed:")
        for file_path, node in issues:
            print(f"- {file_path.relative_to(ROOT)}: {node}")
        return 1

    print("Owner English-only check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
