# Contributing

Thank you for helping to improve the Claude Code Ultimate Pack. This page explains how to add a skill or update one under the v3.0.0 format. The format itself is described in [docs/skill-structure.md](./docs/skill-structure.md).

## Contents

1. [Ground rules](#ground-rules)
2. [Setup](#setup)
3. [Add a skill](#add-a-skill)
4. [Update a skill](#update-a-skill)
5. [Quality bar](#quality-bar)
6. [Validate](#validate)
7. [Commits](#commits)
8. [Pull requests](#pull-requests)
9. [Review](#review)
10. [Reporting issues](#reporting-issues)

## Ground rules

- Be respectful and constructive in issues and reviews.
- One skill per folder under `skills/`, following the [Agent Skills format](https://code.claude.com/docs/en/skills) and the layout in [docs/skill-structure.md](./docs/skill-structure.md).
- Facts come from official documentation or release notes. Do not guess versions, options or package names.
- Files are UTF-8 without BOM, with LF line endings, in English.
- Do not add attribution trailers or tool-generated signatures to files, commits or pull requests.

## Setup

```bash
git clone https://github.com/mjs19971997/Claude-Code-Ultimate-Pack.git
cd Claude-Code-Ultimate-Pack
python3 -m pip install pyyaml
git checkout -b add-<skill-name>
```

If you work from a fork, clone your fork and add this repository as `upstream`.

## Add a skill

1. **Choose the name.** Lowercase letters, digits and hyphens, at most 64 characters, in the style of the existing names (for example `redis-expert`). Check [docs/skill-index.md](./docs/skill-index.md) first: if an existing skill covers the topic, update it instead of adding a new one.
2. **Copy the template.**

   ```bash
   cp -r templates/skill-template skills/<skill-name>
   ```

   Then edit `skills/<skill-name>/SKILL.md`: set `name` to the folder name and replace every placeholder.
3. **Write the description** as "what it does. Use when triggers. Not for area (use other-skill)." Aim for 300-700 characters, at most 1024. Use real triggers (tool names, file names, commands, symptoms) and name the sibling skill for each confusable area.
4. **Verify the facts.** Read the official documentation and release notes for every version, option, default and API you mention. Record what you checked in the `> Verified against ... (YYYY-MM).` line. Run any example you can.
5. **Fill the sections.** Keep the numbered order from the template and drop sections with nothing specific to say. Keep `SKILL.md` to 200-400 lines and move deep material to one to five files under `references/`, each linked from the References section.
6. **Register the skill.** Add its name to the right category in `CATEGORIES` in `scripts/generate_skill_index.py`, and add a row to the table in [README.md](./README.md#skills).
7. **Validate and regenerate the index** (see [Validate](#validate)).
8. Update [CHANGELOG.md](./CHANGELOG.md) under `[Unreleased]`.

## Update a skill

- Re-check the changed facts against official documentation and update the `Verified against` line and its date.
- Keep the structure and the line limits; if a section grows, move the detail into `references/`.
- When you rename or merge a skill, update every mention in the docs, the category list in `scripts/generate_skill_index.py`, the README tables and the changelog. Mention the old name in the target's description so the old topic still triggers it.
- Bump `metadata.version` for behavior changes: patch for corrections, minor for new coverage, major for a restructure.

## Quality bar

- **Accurate:** versions, flags and APIs exist and behave as written.
- **Specific:** rules say what to do and why, with exact option names; no filler or generic advice.
- **Safe:** examples use placeholders for secrets, parameterized queries, verified TLS and least privilege.
- **Focused:** the skill states what it does not cover and points to the skill that does.
- **Self-contained examples:** two or three examples that compile or run as shown, with balanced code fences.
- **Neutral:** no persona lines, no instructions about reply style, no claims of final authority.

## Validate

Run from the repository root:

```bash
python3 scripts/validate_skills.py              # read-only; exits 1 on errors
python3 scripts/generate_skill_index.py         # rewrites docs/skill-index.md
python3 scripts/generate_skill_index.py --check # exits 1 if the index is stale
```

Fix every error and warning for your skill. Commit the regenerated `docs/skill-index.md`; do not edit it by hand. Also check that relative links in files you changed resolve.

To try the skill, copy it to `~/.claude/skills/<skill-name>/` (or a project's `.claude/skills/`), start a new Claude Code session, and ask a question that matches the description. Check that the skill loads, either from the request or by calling `/<skill-name>`.

## Commits

Write plain, imperative messages with a short subject (about 72 characters or fewer) and an optional body that explains why:

```text
Fix HEALTHCHECK defaults in docker-expert

The start-interval option needs Engine 25.0 or later; note the
version and correct the table in section 2.
```

Commit each logical change on its own. Do not add trailers such as co-author or generator lines.

## Pull requests

1. Push your branch and open a pull request against `main`.
2. Describe what changed and which sources you used to verify it.
3. Confirm in the description that `validate_skills.py` reports no errors for your skill and that the index is up to date.
4. Link any related issue with `Closes #<number>`.
5. Respond to review comments by pushing further commits; a maintainer merges once the checks pass and the review is done.

## Review

Reviewers check, in this order:

1. The validator passes and `generate_skill_index.py --check` exits 0.
2. The frontmatter and the description follow the format, with no overlap that would trigger the wrong skill.
3. Versions and claims match official documentation.
4. Examples are correct and safe.
5. The structure matches [docs/skill-structure.md](./docs/skill-structure.md) and the length limits.
6. Links resolve and the docs and changelog reflect the change.

## Reporting issues

Open an issue on [GitHub](https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/issues). For a wrong or outdated statement, give the skill name, the section, what is wrong and a link to the source that shows the correct behavior. For a skill that does not trigger, include the prompt you used and the installed skill's `description`.

For a security problem in this repository, do not post details in a public issue; contact the maintainer through the GitHub profile linked below.

## License

By contributing you agree that your contribution is licensed under the [MIT License](./LICENSE). Author and maintainer: Mostafa Jalili Sanjarani ([mjs19971997](https://github.com/mjs19971997)).
