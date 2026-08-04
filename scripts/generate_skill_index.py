#!/usr/bin/env python3
"""Generate docs/skill-index.md from the migration manifest."""

import json
from pathlib import Path

MANIFEST_PATH = Path("/home/z/my-project/workspace/migration-manifest.json")
OUTPUT_PATH = Path("/home/z/my-project/workspace/Claude-Code-Ultimate-Pack-v2/docs/skill-index.md")

DOMAIN_ORDER = [
    "frontend", "backend", "database", "blockchain", "mobile",
    "devops", "architecture", "security", "testing", "ai", "seo",
]

DOMAIN_TITLES = {
    "frontend": "Frontend",
    "backend": "Backend",
    "database": "Database",
    "blockchain": "Blockchain",
    "mobile": "Mobile",
    "devops": "DevOps",
    "architecture": "Architecture",
    "security": "Security",
    "testing": "Testing",
    "ai": "AI",
    "seo": "SEO",
}

DOMAIN_COVERAGE = {
    "frontend": "React 19, Next.js 15, TypeScript, TailwindCSS, shadcn/ui, UI/UX, accessibility, performance, Framer Motion",
    "backend": "Node.js, Express, NestJS, REST, GraphQL, authn, authz, DDD, microservices, Clean Architecture",
    "database": "PostgreSQL, Prisma, MongoDB, Redis, ElasticSearch",
    "blockchain": "Ethereum, Solidity, Hardhat, Foundry, Web3.js, ethers.js, OpenZeppelin, enterprise blockchain, smart-contract security, DeFi, DAO, NFT, Hyperledger Fabric",
    "mobile": "Android Kotlin, Jetpack Compose, Android architecture, Swift, SwiftUI, UIKit",
    "devops": "Docker, Docker Compose, Linux, Ubuntu Server, Nginx, Git, GitHub, GitHub Actions, CI/CD, Kubernetes, Terraform, AWS",
    "architecture": "Software architecture, solution architecture, enterprise architecture, system design, performance optimization, scalability, refactoring, code review",
    "security": "OWASP Top 10, secure coding, JWT, OAuth2, API security",
    "testing": "Vitest, Jest, Playwright, Cypress, unit, integration, end-to-end",
    "ai": "Agent architecture, MCP, LangGraph, LangChain, CrewAI, OpenAI SDK, Anthropic SDK, Gemini SDK, prompt engineering, RAG, vector databases, memory systems, multi-agent",
    "seo": "Technical SEO, Core Web Vitals, Schema.org, structured data",
}


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    skills = manifest["skills_migrated"]

    # Group by domain
    by_domain: dict[str, list[dict]] = {}
    for s in skills:
        by_domain.setdefault(s["domain"], []).append(s)

    # Sort within each domain by skill_name
    for d in by_domain:
        by_domain[d].sort(key=lambda x: x["skill_name"])

    total = len(skills)

    lines: list[str] = []
    lines.append("# Skill Index")
    lines.append("")
    lines.append(f"A complete, flat index of every skill in the Claude Code Ultimate Pack. All {total} skills live at `skills/<skill-name>/SKILL.md` per the [official Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills).")
    lines.append("")
    lines.append(f"**Total skills: {total}** across {len(by_domain)} domains.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")
    for d in DOMAIN_ORDER:
        if d in by_domain:
            anchor = DOMAIN_TITLES[d].lower()
            lines.append(f"- [{DOMAIN_TITLES[d]} ({len(by_domain[d])} skills)](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    for d in DOMAIN_ORDER:
        if d not in by_domain:
            continue
        title = DOMAIN_TITLES[d]
        coverage = DOMAIN_COVERAGE.get(d, "")
        skills_in_domain = by_domain[d]
        lines.append(f"## {title} ({len(skills_in_domain)} skills)")
        lines.append("")
        lines.append(f"**Coverage**: {coverage}.")
        lines.append("")
        lines.append("| Skill Name | Folder | Description |")
        lines.append("|---|---|---|")
        for s in skills_in_domain:
            name = s["skill_name"]
            title_val = s["title"]
            desc = s["description"].replace("|", "\\|").replace("\n", " ")
            # Truncate very long descriptions for table readability
            if len(desc) > 180:
                desc = desc[:177] + "..."
            folder = f"`skills/{name}/`"
            lines.append(f"| `{name}` | {folder} | {desc} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Cross-domain usage notes
    lines.append("## How to Use This Index")
    lines.append("")
    lines.append("1. **Find by domain**: scan the tables above to find skills relevant to your work.")
    lines.append("2. **Find by name**: use your editor's find-in-page (`Cmd/Ctrl + F`) to search for a specific skill name.")
    lines.append("3. **Activate**: skills auto-activate based on the `description` field in their YAML frontmatter. You can also force-activate with `/skill <skill-name>`.")
    lines.append("4. **Compose**: multiple skills can be active simultaneously. For example, building an authenticated REST API with PostgreSQL naturally composes `nestjs-expert`, `authentication-expert`, `postgresql-expert`, and `jest-expert`.")
    lines.append("")
    lines.append("## See Also")
    lines.append("")
    lines.append("- [`docs/usage-guide.md`](./usage-guide.md) — detailed usage patterns")
    lines.append("- [`examples/example-usage.md`](../examples/example-usage.md) — real-world scenarios")
    lines.append("- [`docs/skill-structure.md`](./skill-structure.md) — the 30-section skill anatomy specification")
    lines.append("- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — how to add a new skill")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Skill index written to: {OUTPUT_PATH}")
    print(f"Total skills indexed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
