#!/usr/bin/env python3
"""
Migrate Claude Code Ultimate Pack skills from legacy layout to the official
Claude Code Agent Skills specification.

Legacy layout:
    skills/<domain>/<skill-name>.md

Official Claude Code Skills layout:
    skills/<skill-name>/SKILL.md

Each SKILL.md must contain YAML frontmatter with at minimum:
    name:        lowercase, hyphens, max 64 chars, must match folder name
    description: substantive — describes what the skill does AND when to use it
Optional but recommended:
    license: MIT
    version: 1.0.0

This script:
  1. Walks every legacy skill file
  2. Extracts name, blockquote description, domain, role level
  3. Generates valid YAML frontmatter
  4. Writes skills/<skill-name>/SKILL.md preserving 100% of original body content
  5. Logs every action
  6. Produces a manifest JSON for downstream validation
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SRC_ROOT = Path("/home/z/my-project/workspace/Claude-Code-Ultimate-Pack")
DST_ROOT = Path("/home/z/my-project/workspace/Claude-Code-Ultimate-Pack-v2")

SRC_SKILLS = SRC_ROOT / "skills"
DST_SKILLS = DST_ROOT / "skills"

# ---------------------------------------------------------------------------
# Domain-aware "when to use" hints. These give Claude Code reliable trigger
# cues beyond the per-skill blockquote. They are intentionally broad so they
# do not fabricate facts — they only describe the kind of work the skill
# covers based on its domain.
# ---------------------------------------------------------------------------
DOMAIN_WHEN_HINT = {
    "ai": "Use this skill when designing AI agents, LLM applications, RAG pipelines, prompt workflows, multi-agent systems, or integrating LLM SDKs.",
    "architecture": "Use this skill when making system-design, scalability, refactoring, code-review, or enterprise-architecture decisions.",
    "backend": "Use this skill when building server-side services, APIs, authentication, authorization, microservices, or domain-driven backend systems.",
    "blockchain": "Use this skill when writing smart contracts, designing DeFi/DAO/NFT systems, or operating blockchain tooling such as Hardhat, Foundry, ethers.js, or Web3.js.",
    "database": "Use this skill when designing schemas, queries, indexing, replication, or operating datastores such as PostgreSQL, MongoDB, Redis, ElasticSearch, or Prisma.",
    "devops": "Use this skill when containerizing, deploying, automating CI/CD, operating clusters, or managing cloud and infrastructure-as-code.",
    "frontend": "Use this skill when building web frontends with React, Next.js, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, or when addressing UI/UX, accessibility, or performance.",
    "mobile": "Use this skill when building Android (Kotlin, Jetpack Compose) or iOS (Swift, SwiftUI, UIKit) applications.",
    "security": "Use this skill when auditing code for OWASP risks, hardening APIs, designing JWT/OAuth2 flows, or enforcing secure-coding standards.",
    "seo": "Use this skill when improving crawlability, indexing, Core Web Vitals, Schema.org markup, or structured data.",
    "testing": "Use this skill when writing unit, integration, or end-to-end tests with Vitest, Jest, Playwright, or Cypress.",
}

# Default fallback if a domain is unknown
DEFAULT_WHEN_HINT = "Use this skill when the task matches the expertise described below."

# ---------------------------------------------------------------------------
# YAML frontmatter builder
# ---------------------------------------------------------------------------
def build_frontmatter(skill_name: str, description: str, domain: str) -> str:
    """
    Build valid YAML frontmatter for a SKILL.md.

    The description field is multi-line using YAML's folded scalar `>`. We
    strip leading/trailing whitespace from each line and collapse blank lines
    so the YAML remains valid.
    """
    # Folded scalar: lines are joined with spaces; blank lines become newlines.
    # We split into "what" (blockquote) and "when" (domain hint) and join with
    # a blank line so they form two paragraphs.
    when_hint = DOMAIN_WHEN_HINT.get(domain, DEFAULT_WHEN_HINT)

    # Sanitize: remove any lone `---` inside description that could break YAML
    what = description.strip().replace("\r", "")
    when = when_hint.strip()

    # Ensure no triple-dash on its own line sneaks through
    what = re.sub(r"(?m)^---\s*$", "—", what)
    when = re.sub(r"(?m)^---\s*$", "—", when)

    # Build folded scalar content. Folded scalars use `>`; a blank line in
    # the content becomes a hard newline in the parsed value.
    folded_lines = []
    folded_lines.append(what)
    folded_lines.append("")  # blank line -> paragraph break
    folded_lines.append(when)
    folded_body = "\n".join(folded_lines)

    fm = (
        "---\n"
        f"name: {skill_name}\n"
        "description: >\n"
        + "".join(f"  {line}\n" for line in folded_body.split("\n"))
        + "license: MIT\n"
        "version: 1.0.0\n"
        "---\n"
    )
    return fm


# ---------------------------------------------------------------------------
# Skill metadata extraction
# ---------------------------------------------------------------------------
H1_RE = re.compile(r"^# Skill:\s*(.+?)\s*$")
BLOCKQUOTE_RE = re.compile(r"^>\s*(.+?)\s*$")
DOMAIN_RE = re.compile(r"\*\*Domain\*\*:\s*([a-zA-Z0-9_-]+)")
ROLE_RE = re.compile(r"\*\*Role Level\*\*:\s*([a-zA-Z]+)")
FILE_RE = re.compile(r"\*\*File\*\*:\s*([^\n]+)")

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def extract_metadata(content: str, skill_name: str, src_path: Path) -> dict:
    """
    Extract metadata from a legacy skill file. The legacy format is:

        # Skill: <Human-Readable Name>
        > <One-sentence description>
        **Domain**: <domain>
        **Role Level**: <Senior|Staff|Principal>
        **File**: <domain>/<skill-name>.md

    Returns a dict with keys: title, description, domain, role_level, body.
    `body` is the full original content with the header block removed and the
    rest preserved verbatim.
    """
    lines = content.split("\n")

    title = None
    description = None
    domain = None
    role_level = None
    file_field = None
    header_end_idx = 0  # index of the first line AFTER the header block

    # The header block is the first contiguous set of non-empty lines that
    # starts with the H1 and ends at the first blank line or `---` separator.
    # We parse line by line.
    for i, line in enumerate(lines):
        if title is None and H1_RE.match(line):
            title = H1_RE.match(line).group(1).strip()
            continue
        if description is None and BLOCKQUOTE_RE.match(line):
            description = BLOCKQUOTE_RE.match(line).group(1).strip()
            continue
        if domain is None:
            m = DOMAIN_RE.search(line)
            if m:
                domain = m.group(1).strip().lower()
                continue
        if role_level is None:
            m = ROLE_RE.search(line)
            if m:
                role_level = m.group(1).strip()
                continue
        if file_field is None:
            m = FILE_RE.search(line)
            if m:
                file_field = m.group(1).strip()
                continue
        # Once we've captured the full header block (H1 + blockquote + 3
        # metadata lines), the next blank line or horizontal rule ends it.
        if title and description and domain and role_level and file_field:
            if line.strip() == "" or line.strip() == "---":
                header_end_idx = i
                break

    if header_end_idx == 0:
        header_end_idx = len(lines)

    # Find the body: everything from header_end_idx onward. We strip a single
    # leading horizontal rule (`---`) if present, since the original used it
    # purely as a visual separator before the Table of Contents.
    body_lines = lines[header_end_idx:]
    # Strip a leading blank line and a leading `---` if present.
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    if body_lines and body_lines[0].strip() == "---":
        body_lines.pop(0)
    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)

    body = "\n".join(body_lines)

    if not title:
        raise ValueError(f"{src_path}: missing H1 '# Skill: <Title>' header")
    if not description:
        raise ValueError(f"{src_path}: missing blockquote description")
    if not domain:
        raise ValueError(f"{src_path}: missing '**Domain**: <domain>' metadata")

    # Validate skill name format
    if not NAME_PATTERN.match(skill_name):
        raise ValueError(
            f"{src_path}: skill name '{skill_name}' is invalid. Must be "
            f"lowercase letters, digits, hyphens; max 64 chars; cannot start "
            f"with a hyphen."
        )

    return {
        "title": title,
        "description": description,
        "domain": domain,
        "role_level": role_level or "Senior",
        "file_field": file_field,
        "body": body,
    }


# ---------------------------------------------------------------------------
# Migration driver
# ---------------------------------------------------------------------------
def migrate() -> dict:
    """Run the full migration. Returns a manifest dict for reporting."""
    if not SRC_SKILLS.is_dir():
        raise SystemExit(f"Source skills directory not found: {SRC_SKILLS}")

    # Wipe destination skills/ to ensure a clean state
    if DST_SKILLS.exists():
        shutil.rmtree(DST_SKILLS)
    DST_SKILLS.mkdir(parents=True, exist_ok=True)

    # Collect all legacy skill files
    legacy_files = sorted(SRC_SKILLS.glob("*/*.md"))
    if not legacy_files:
        raise SystemExit(f"No legacy skill files found under {SRC_SKILLS}")

    manifest = {
        "migration_started_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SRC_ROOT),
        "destination_root": str(DST_ROOT),
        "spec_reference": "https://code.claude.com/docs/en/skills",
        "skills_migrated": [],
        "skills_failed": [],
        "files_created": [],
        "files_deleted": [],
        "summary": {},
    }

    for src_path in legacy_files:
        skill_name = src_path.stem  # e.g. "ai-agent-architect"
        domain = src_path.parent.name  # e.g. "ai"
        try:
            content = src_path.read_text(encoding="utf-8")
            meta = extract_metadata(content, skill_name, src_path)
        except Exception as exc:
            manifest["skills_failed"].append({
                "source": str(src_path),
                "skill_name": skill_name,
                "error": str(exc),
            })
            continue

        # Build new SKILL.md content: YAML frontmatter + body
        frontmatter = build_frontmatter(
            skill_name=skill_name,
            description=meta["description"],
            domain=meta["domain"],
        )
        # Ensure body ends with a single trailing newline
        body = meta["body"].rstrip() + "\n"
        new_content = frontmatter + "\n" + body

        # Write to skills/<skill-name>/SKILL.md
        skill_dir = DST_SKILLS / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        dst_path = skill_dir / "SKILL.md"
        dst_path.write_text(new_content, encoding="utf-8")

        manifest["skills_migrated"].append({
            "skill_name": skill_name,
            "domain": meta["domain"],
            "role_level": meta["role_level"],
            "title": meta["title"],
            "source_path": str(src_path),
            "destination_path": str(dst_path),
            "source_lines": len(content.split("\n")),
            "destination_lines": len(new_content.split("\n")),
            "description": meta["description"],
        })
        manifest["files_created"].append(str(dst_path))
        manifest["files_deleted"].append(str(src_path))

    manifest["summary"] = {
        "total_legacy_files": len(legacy_files),
        "migrated": len(manifest["skills_migrated"]),
        "failed": len(manifest["skills_failed"]),
        "domains": sorted({s["domain"] for s in manifest["skills_migrated"]}),
    }
    manifest["migration_finished_at"] = datetime.now(timezone.utc).isoformat()
    return manifest


def main() -> int:
    manifest = migrate()
    # Write manifest to workspace for downstream validation
    manifest_path = DST_ROOT.parent / "migration-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest written to: {manifest_path}")
    print(f"Migrated: {manifest['summary']['migrated']} / {manifest['summary']['total_legacy_files']}")
    print(f"Failed: {manifest['summary']['failed']}")
    print(f"Domains: {', '.join(manifest['summary']['domains'])}")
    if manifest["skills_failed"]:
        print("\nFailures:")
        for f in manifest["skills_failed"]:
            print(f"  - {f['skill_name']}: {f['error']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
