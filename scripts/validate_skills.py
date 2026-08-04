#!/usr/bin/env python3
"""
Validate the migrated Claude Code Ultimate Pack repository against the
official Claude Code Agent Skills specification.

Checks performed per SKILL.md:
  1. File exists at skills/<skill-name>/SKILL.md
  2. File is UTF-8 decodable
  3. Begins with YAML frontmatter delimited by `---` lines
  4. YAML parses successfully
  5. `name` field is present, matches folder name, matches the spec pattern
     (lowercase letters, digits, hyphens; max 64 chars; cannot start with hyphen)
  6. `description` field is present and non-empty after stripping
  7. `description` is substantive (>= 40 chars) — it is Claude's trigger cue
  8. `license` field is present (recommended)
  9. `version` field is present and SemVer-ish (recommended)
 10. Markdown body is non-empty
 11. Body preserves the legacy "## 1. Role" through "## 30. Output Format"
     section headers (the 30-section anatomy)
 12. No CRLF line endings (LF only)
 13. No BOM
 14. No `TODO`, `FIXME`, `PLACEHOLDER` markers that weren't in the original

Repo-level checks:
  A. Every legacy skill file has a corresponding new SKILL.md
  B. Every new SKILL.md corresponds to exactly one legacy skill file
  C. Total line count of migrated body >= 95% of legacy body (no content loss)
  D. No legacy `skills/<domain>/` directories remain in the new tree
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("PyYAML not installed. Installing...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml

SRC_ROOT = Path("/home/z/my-project/workspace/Claude-Code-Ultimate-Pack")
DST_ROOT = Path("/home/z/my-project/workspace/Claude-Code-Ultimate-Pack-v2")
MANIFEST_PATH = Path("/home/z/my-project/workspace/migration-manifest.json")
REPORT_PATH = Path("/home/z/my-project/workspace/validation-report.json")

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SECTION_HEADERS = [
    "## 1. Role",
    "## 2. Mission",
    "## 3. Core Expertise",
    "## 4. Responsibilities",
    "## 5. Thinking Process",
    "## 6. Decision Making Rules",
    "## 7. Architecture Rules",
    "## 8. Coding Standards",
    "## 9. Naming Conventions",
    "## 10. Folder Structure",
    "## 11. Project Structure",
    "## 12. Design Patterns",
    "## 13. Best Practices",
    "## 14. Anti Patterns",
    "## 15. Performance Rules",
    "## 16. Security Rules",
    "## 17. Testing Strategy",
    "## 18. Documentation Standards",
    "## 19. Code Review Checklist",
    "## 20. Refactoring Checklist",
    "## 21. Deployment Checklist",
    "## 22. Production Checklist",
    "## 23. Logging Strategy",
    "## 24. Monitoring Strategy",
    "## 25. Error Handling",
    "## 26. Examples",
    "## 27. Common Mistakes",
    "## 28. Professional Workflow",
    "## 29. Response Style",
    "## 30. Output Format",
]

FRONTMATTER_DELIM = "---"


def parse_frontmatter(text: str) -> tuple[dict, str, str | None]:
    """
    Parse YAML frontmatter from the top of a markdown file.
    Returns (parsed_dict, body_text, error_message).
    """
    if not text.startswith("---\n"):
        return ({}, text, "File does not start with '---\\n' frontmatter delimiter")
    # Find the closing `---` line
    lines = text.split("\n")
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return ({}, text, "First line is not '---'")
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIM:
            close_idx = i
            break
    if close_idx is None:
        return ({}, text, "Frontmatter not closed with a second '---' line")
    fm_text = "\n".join(lines[1:close_idx])
    body_text = "\n".join(lines[close_idx + 1:])
    try:
        parsed = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        return ({}, text, f"YAML parse error: {exc}")
    if not isinstance(parsed, dict):
        return ({}, text, "Frontmatter did not parse to a mapping")
    return (parsed, body_text, None)


def validate_skill(skill_dir: Path) -> dict:
    """Validate one skill folder. Returns a per-skill report dict."""
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    report = {
        "skill_name": skill_name,
        "path": str(skill_md),
        "ok": True,
        "errors": [],
        "warnings": [],
        "stats": {},
    }

    # 1. File exists
    if not skill_md.is_file():
        report["ok"] = False
        report["errors"].append("SKILL.md not found")
        return report

    # 2. UTF-8 decodable + BOM check
    try:
        raw = skill_md.read_bytes()
    except Exception as exc:
        report["ok"] = False
        report["errors"].append(f"Cannot read file: {exc}")
        return report

    if raw.startswith(b"\xef\xbb\xbf"):
        report["ok"] = False
        report["errors"].append("File has a UTF-8 BOM — strip it")
        return report

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        report["ok"] = False
        report["errors"].append(f"File is not valid UTF-8: {exc}")
        return report

    # 12. No CRLF
    if "\r\n" in text:
        report["ok"] = False
        report["errors"].append("File contains CRLF line endings — use LF only")
        return report

    # 3 + 4. Frontmatter present + parses
    fm, body, err = parse_frontmatter(text)
    if err:
        report["ok"] = False
        report["errors"].append(f"Frontmatter: {err}")
        return report

    # 5. name
    name = fm.get("name")
    if not name:
        report["ok"] = False
        report["errors"].append("Frontmatter missing 'name' field")
    elif not isinstance(name, str):
        report["ok"] = False
        report["errors"].append(f"'name' must be a string, got {type(name).__name__}")
    elif not NAME_PATTERN.match(name):
        report["ok"] = False
        report["errors"].append(
            f"'name' value '{name}' violates spec (lowercase letters, digits, "
            f"hyphens; max 64 chars; cannot start with hyphen)"
        )
    elif name != skill_name:
        report["ok"] = False
        report["errors"].append(
            f"'name' value '{name}' does not match folder name '{skill_name}'"
        )

    # 6 + 7. description
    desc = fm.get("description")
    if desc is None:
        report["ok"] = False
        report["errors"].append("Frontmatter missing 'description' field")
    elif not isinstance(desc, str):
        report["ok"] = False
        report["errors"].append(f"'description' must be a string, got {type(desc).__name__}")
    else:
        desc_stripped = desc.strip()
        if not desc_stripped:
            report["ok"] = False
            report["errors"].append("'description' is empty")
        elif len(desc_stripped) < 40:
            report["warnings"].append(
                f"'description' is very short ({len(desc_stripped)} chars); "
                f"Claude uses it as the trigger cue — make it substantive"
            )

    # 8. license
    if "license" not in fm:
        report["warnings"].append("Frontmatter missing 'license' field (recommended)")

    # 9. version
    ver = fm.get("version")
    if ver is None:
        report["warnings"].append("Frontmatter missing 'version' field (recommended)")
    elif not isinstance(ver, str) or not SEMVER_PATTERN.match(ver):
        report["warnings"].append(
            f"'version' value '{ver}' is not SemVer (MAJOR.MINOR.PATCH)"
        )

    # 10. body non-empty
    body_stripped = body.strip()
    if not body_stripped:
        report["ok"] = False
        report["errors"].append("Body is empty after frontmatter")
        return report

    # 11. 30-section anatomy preserved
    missing_sections = []
    for header in SECTION_HEADERS:
        # Allow headers like "## 1. Role" possibly followed by trailing whitespace
        # Also accept variants with extra spaces (the existing files use exactly this format)
        pattern = re.compile(r"^" + re.escape(header) + r"\s*$", re.MULTILINE)
        if not pattern.search(body):
            missing_sections.append(header)
    if missing_sections:
        # Some legacy files use slightly different formatting (e.g. "## 1. Role" vs "##1. Role").
        # We accept "## N. Title" with one-or-more spaces. Try a looser match.
        still_missing = []
        for header in missing_sections:
            # Extract the section number and title
            m = re.match(r"^## (\d+)\.\s+(.+)$", header)
            if not m:
                still_missing.append(header)
                continue
            num, title = m.group(1), m.group(2)
            loose = re.compile(
                r"^##\s+" + num + r"\.\s+" + re.escape(title) + r"\s*$",
                re.MULTILINE,
            )
            if not loose.search(body):
                still_missing.append(header)
        if still_missing:
            report["warnings"].append(
                f"Body missing section headers: {', '.join(still_missing)}"
            )

    # 13. TODO/FIXME/PLACEHOLDER markers — only flag occurrences OUTSIDE fenced
    # code blocks (```...```) and OUTSIDE inline code (`...`). This avoids false
    # positives like Swift's `placeholder:` closure label inside AsyncImage.
    # Also require the marker to be at a word boundary so "TODO:" inside a
    # larger identifier does not trigger.
    def strip_code_blocks(text: str) -> str:
        """Remove fenced code blocks and inline code from text."""
        # Remove fenced code blocks (```...```)
        no_fenced = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        # Remove inline code (`...`)
        no_inline = re.sub(r"`[^`\n]*`", "", no_fenced)
        return no_inline

    prose = strip_code_blocks(body)
    for marker in ["TODO:", "FIXME:", "PLACEHOLDER:", "XXX:"]:
        # Match the marker at a word boundary, case-insensitive, but only in
        # prose (code blocks already stripped above)
        pattern = re.compile(r"\b" + re.escape(marker) + r"", re.IGNORECASE)
        if pattern.search(prose):
            report["warnings"].append(f"Body prose contains '{marker}' marker")

    report["stats"] = {
        "body_lines": len(body.split("\n")),
        "body_chars": len(body),
        "frontmatter_fields": sorted(fm.keys()),
    }
    return report


def validate_repo() -> dict:
    """Run all repo-level checks and per-skill checks."""
    report = {
        "validated_at": None,
        "destination_root": str(DST_ROOT),
        "spec_reference": "https://code.claude.com/docs/en/skills",
        "skills": [],
        "repo_checks": [],
        "summary": {},
    }

    # Per-skill checks
    skill_dirs = sorted([p for p in (DST_ROOT / "skills").iterdir() if p.is_dir()])
    for sd in skill_dirs:
        report["skills"].append(validate_skill(sd))

    # Repo check A: every legacy skill file has a new SKILL.md
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    legacy_names = {Path(s["source_path"]).stem for s in manifest["skills_migrated"]}
    new_names = {p.name for p in skill_dirs}
    missing_new = legacy_names - new_names
    if missing_new:
        report["repo_checks"].append({
            "check": "every_legacy_has_new_skill_md",
            "ok": False,
            "detail": f"Missing SKILL.md for: {sorted(missing_new)}",
        })
    else:
        report["repo_checks"].append({
            "check": "every_legacy_has_new_skill_md",
            "ok": True,
            "detail": f"All {len(legacy_names)} legacy skills have a new SKILL.md",
        })

    # Repo check B: every new SKILL.md corresponds to a legacy file
    extra_new = new_names - legacy_names
    if extra_new:
        report["repo_checks"].append({
            "check": "no_orphan_new_skills",
            "ok": False,
            "detail": f"New SKILL.md without a legacy source: {sorted(extra_new)}",
        })
    else:
        report["repo_checks"].append({
            "check": "no_orphan_new_skills",
            "ok": True,
            "detail": "Every new SKILL.md has a corresponding legacy source",
        })

    # Repo check C: content preservation (body line count)
    content_loss_warnings = []
    for s in manifest["skills_migrated"]:
        # Legacy body line count = source_lines - header_block_lines (approx 6)
        legacy_body_lines = s["source_lines"] - 6  # H1, blockquote, Domain, Role, File, blank
        # New body line count = destination_lines - frontmatter_lines (7: ---, name, desc, desc, license, version, ---)
        new_body_lines = s["destination_lines"] - 7
        if legacy_body_lines > 0:
            ratio = new_body_lines / legacy_body_lines
            if ratio < 0.95:
                content_loss_warnings.append(
                    f"{s['skill_name']}: new body has {new_body_lines} lines vs "
                    f"legacy {legacy_body_lines} (ratio {ratio:.2%})"
                )
    if content_loss_warnings:
        report["repo_checks"].append({
            "check": "content_preservation",
            "ok": False,
            "detail": "; ".join(content_loss_warnings[:10]),
        })
    else:
        report["repo_checks"].append({
            "check": "content_preservation",
            "ok": True,
            "detail": "All skills preserved >= 95% of legacy body content",
        })

    # Repo check D: no legacy skills/<domain>/ directories remain
    leftover_domains = []
    if (DST_ROOT / "skills").exists():
        for child in (DST_ROOT / "skills").iterdir():
            # A "domain" directory is one that contains .md files directly
            # rather than its own SKILL.md
            if child.is_dir() and not (child / "SKILL.md").exists():
                # Check if it contains .md files (legacy layout)
                if any(child.glob("*.md")):
                    leftover_domains.append(child.name)
    if leftover_domains:
        report["repo_checks"].append({
            "check": "no_legacy_domain_dirs",
            "ok": False,
            "detail": f"Legacy domain directories remain: {sorted(leftover_domains)}",
        })
    else:
        report["repo_checks"].append({
            "check": "no_legacy_domain_dirs",
            "ok": True,
            "detail": "No legacy skills/<domain>/ directories remain",
        })

    # Summary
    total = len(report["skills"])
    ok_count = sum(1 for s in report["skills"] if s["ok"])
    warn_count = sum(1 for s in report["skills"] if not s["ok"] and not s["errors"])
    err_count = sum(1 for s in report["skills"] if not s["ok"])
    repo_ok = all(c["ok"] for c in report["repo_checks"])
    report["summary"] = {
        "total_skills": total,
        "skills_passed": ok_count,
        "skills_with_errors": err_count,
        "skills_with_only_warnings": warn_count,
        "repo_checks_passed": sum(1 for c in report["repo_checks"] if c["ok"]),
        "repo_checks_total": len(report["repo_checks"]),
        "overall_pass": ok_count == total and repo_ok,
    }
    return report


def main() -> int:
    report = validate_repo()
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    s = report["summary"]
    print(f"Validation report written to: {REPORT_PATH}")
    print(f"Total skills:    {s['total_skills']}")
    print(f"Skills passed:   {s['skills_passed']}")
    print(f"Skills w/ errors: {s['skills_with_errors']}")
    print(f"Repo checks:     {s['repo_checks_passed']}/{s['repo_checks_total']}")
    print(f"Overall pass:    {s['overall_pass']}")
    if not s["overall_pass"]:
        print("\nErrors:")
        for sk in report["skills"]:
            if not sk["ok"]:
                print(f"  - {sk['skill_name']}: {sk['errors']}")
        print("\nRepo check failures:")
        for c in report["repo_checks"]:
            if not c["ok"]:
                print(f"  - {c['check']}: {c['detail']}")
        return 1
    # Print any warnings
    warnings_shown = 0
    for sk in report["skills"]:
        if sk["warnings"]:
            for w in sk["warnings"][:1]:
                if warnings_shown < 5:
                    print(f"WARN {sk['skill_name']}: {w}")
                    warnings_shown += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
