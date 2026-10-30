#!/usr/bin/env python3
"""
Validate every skill in this repository against the Agent Skills format.

Usage (from anywhere):
    python scripts/validate_skills.py            # human-readable report
    python scripts/validate_skills.py --json     # machine-readable report on stdout

The script only reads files. It exits with status 1 when any error is found.

Checks per skills/<name>/ folder (and templates/skill-template/):
  - SKILL.md exists, is UTF-8 without BOM and uses LF line endings
  - YAML frontmatter parses; only the allowed top-level keys are used
  - `name` matches the folder name and the naming pattern
  - `description` is 40-1024 characters
  - `license` is present; `metadata.version` is SemVer
  - no "Response Style" / "Output Format" sections and no persona lines
  - every in-file anchor link (#...) points at a real heading
  - every relative link (references/*.md, ...) points at an existing file
  - code fences are balanced
  - SKILL.md length warning outside 80-450 lines
  - no attribution trailers ("Co-Authored-By", "Generated with")
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("PyYAML is required: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATE_DIR = REPO_ROOT / "templates" / "skill-template"

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
MIN_DESC, MAX_DESC = 40, 1024
MIN_LINES, MAX_LINES = 80, 450

FORBIDDEN_HEADINGS = re.compile(r"^#{1,6}\s+(\d+\.\s*)?(Response Style|Output Format)\s*$", re.I | re.M)
FORBIDDEN_TEXT = [
    re.compile(r"co-authored-by", re.I),
    re.compile(r"generated with", re.I),
    re.compile(r"\bfinal authority\b", re.I),
    re.compile(r"\bprincipal authority\b", re.I),
    re.compile(r"^\s*You are an? (Principal|Senior|Staff|Lead)\b", re.M),
]
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")


def github_slug(text: str) -> str:
    """Approximate GitHub's heading anchor algorithm."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def strip_code(lines: list[str]) -> tuple[list[str], bool]:
    """Return lines outside fenced code blocks and whether fences are balanced."""
    out, fence = [], None
    for line in lines:
        m = FENCE_PATTERN.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence = marker
                continue
            if marker[0] == fence[0] and len(marker) >= len(fence) and line.strip() == marker:
                fence = None
                continue
        if fence is None:
            out.append(line)
    return out, fence is None


def parse_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    if not text.startswith("---\n"):
        return None, text, "file must start with '---' frontmatter"
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text, "frontmatter is not closed with '---'"
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        return None, text, f"YAML error: {exc}"
    if not isinstance(data, dict):
        return None, text, "frontmatter is not a mapping"
    return data, text[end + 5:], None


def check_markdown(path: Path, text: str, report: dict) -> None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    lines = text.split("\n")
    prose, balanced = strip_code(lines)
    if not balanced:
        report["errors"].append(f"{rel}: unbalanced code fence")
    anchors, seen = set(), {}
    for line in prose:
        m = HEADING_PATTERN.match(line)
        if m:
            slug = github_slug(m.group(2))
            n = seen.get(slug, 0)
            anchors.add(slug if n == 0 else f"{slug}-{n}")
            seen[slug] = n + 1
    for line in prose:
        for target in LINK_PATTERN.findall(line):
            if re.match(r"^[a-z]+:", target):
                continue
            file_part, _, anchor = target.partition("#")
            if not file_part:
                if anchor not in anchors:
                    report["errors"].append(f"{rel}: broken anchor #{anchor}")
            elif not (path.parent / file_part).exists():
                report["errors"].append(f"{rel}: broken link {file_part}")
    for pattern in FORBIDDEN_TEXT:
        if pattern.search(text):
            report["errors"].append(f"{rel}: forbidden text matching /{pattern.pattern}/")
    if FORBIDDEN_HEADINGS.search("\n".join(prose)):
        report["errors"].append(f"{rel}: has a Response Style / Output Format section")


def validate_skill(skill_dir: Path, expected_name: str) -> dict:
    report = {"skill": expected_name, "errors": [], "warnings": [], "lines": 0}
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        report["errors"].append("SKILL.md not found")
        return report

    for md in sorted(skill_dir.rglob("*.md")):
        raw = md.read_bytes()
        rel = md.relative_to(REPO_ROOT).as_posix()
        if raw.startswith(b"\xef\xbb\xbf"):
            report["errors"].append(f"{rel}: has a UTF-8 BOM")
        if b"\r\n" in raw:
            report["errors"].append(f"{rel}: has CRLF line endings")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            report["errors"].append(f"{rel}: not UTF-8 ({exc})")
            continue
        if md == skill_md:
            continue
        check_markdown(md, text, report)

    text = skill_md.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n").lstrip("﻿")
    report["lines"] = text.count("\n") + 1
    meta, body, err = parse_frontmatter(text)
    if err:
        report["errors"].append(err)
        return report

    extra = set(meta) - ALLOWED_KEYS
    if extra:
        report["errors"].append(f"unsupported frontmatter keys: {sorted(extra)}")

    name = meta.get("name")
    if name != expected_name:
        report["errors"].append(f"name {name!r} does not match folder {expected_name!r}")
    elif not NAME_PATTERN.match(name):
        report["errors"].append(f"name {name!r} does not match {NAME_PATTERN.pattern}")

    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        report["errors"].append("description is missing")
    else:
        n = len(desc.strip())
        if n < MIN_DESC or n > MAX_DESC:
            report["errors"].append(f"description is {n} characters (allowed {MIN_DESC}-{MAX_DESC})")
        if "use when" not in desc.lower():
            report["warnings"].append("description has no 'Use when' trigger sentence")

    if "license" not in meta:
        report["warnings"].append("license is missing")
    version = (meta.get("metadata") or {}).get("version") if isinstance(meta.get("metadata"), dict) else None
    if version is None:
        report["warnings"].append("metadata.version is missing")
    elif not SEMVER_PATTERN.match(str(version)):
        report["errors"].append(f"metadata.version {version!r} is not SemVer")

    if not body.strip():
        report["errors"].append("body is empty")
    if not (MIN_LINES <= report["lines"] <= MAX_LINES):
        report["warnings"].append(f"SKILL.md has {report['lines']} lines (target {MIN_LINES}-{MAX_LINES})")
    check_markdown(skill_md, text, report)
    return report


def main() -> int:
    targets = [(d, d.name) for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir()]
    if TEMPLATE_DIR.is_dir():
        targets.append((TEMPLATE_DIR, "skill-template"))
    reports = [validate_skill(d, name) for d, name in targets]
    errors = sum(len(r["errors"]) for r in reports)
    warnings = sum(len(r["warnings"]) for r in reports)

    if "--json" in sys.argv:
        print(json.dumps({"skills": len(targets), "errors": errors, "warnings": warnings,
                          "reports": reports}, indent=2))
    else:
        for r in reports:
            for e in r["errors"]:
                print(f"ERROR   {r['skill']}: {e}")
            for w in r["warnings"]:
                print(f"WARN    {r['skill']}: {w}")
        print(f"\n{len(targets)} skill folders checked: {errors} errors, {warnings} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
