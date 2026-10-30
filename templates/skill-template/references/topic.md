# Topic Reference (sample)

Reference files hold material that is too long for `SKILL.md`: full examples, option tables, migration notes. Claude opens them only when the task needs that detail, so each file should stand on its own.

## Contents
1. [When to add a reference file](#when-to-add-a-reference-file)
2. [Structure of a reference file](#structure-of-a-reference-file)
3. [Placeholder example](#placeholder-example)

## When to add a reference file

- A section in `SKILL.md` would grow beyond about 20 lines.
- The material applies to only some tasks (for example one framework, one cloud provider or one migration path).
- A long example or a complete configuration file is needed.

Use one to five files per skill, named after the topic in lowercase with hyphens (`compose.md`, `image-security.md`). Link each from the References section of `SKILL.md` with a one-line description.

## Structure of a reference file

- Start with a title and a short statement of what the file covers.
- Add a Contents list when the file has more than three sections.
- State the versions the content was checked against if they differ from `SKILL.md`.
- Keep headings descriptive; do not number them.

## Placeholder example

```bash
# Replace with a command from your domain and say what it demonstrates.
echo "reference files are plain Markdown"
```

Delete this file, or replace it with real references, when you copy the template.
