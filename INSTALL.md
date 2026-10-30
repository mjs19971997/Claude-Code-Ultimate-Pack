# Installation Guide

This guide covers installing, updating and removing the Claude Code Ultimate Pack v3.0.0 (67 skills) on Linux, macOS and Windows.

Every command here works on **this pack's own skill folders only**. Nothing in this guide deletes the skills folder or skills that came from somewhere else. Installing never overwrites an existing folder: if a skill with the same name is already there, it is skipped and reported.

---

## Contents

1. [Requirements](#requirements)
2. [Where skills live](#where-skills-live)
3. [Get the pack](#get-the-pack)
4. [Install](#install)
5. [Check the install](#check-the-install)
6. [Upgrade](#upgrade)
7. [Uninstall](#uninstall)
8. [Troubleshooting](#troubleshooting)

---

## Requirements

- [Claude Code](https://code.claude.com/docs/en) installed (`claude --version` works).
- Git, or a browser to download the repository as a ZIP.
- Optional: Python 3.9+ with PyYAML, to run the validator in `scripts/`.

## Where skills live

Each skill is a folder that contains a `SKILL.md` file. Claude Code loads skills from:

| Scope | Folder | Applies to |
|---|---|---|
| Personal | `~/.claude/skills/<skill-name>/` (Windows: `%USERPROFILE%\.claude\skills\<skill-name>\`) | All your projects on this machine |
| Project | `<project>/.claude/skills/<skill-name>/` | Sessions in that project; commit it to share with your team |

If the same skill name exists in both places, the personal one wins. See the official [skills documentation](https://code.claude.com/docs/en/skills) for all locations.

You do not have to install all 67 skills. Installing only the skills you use keeps the skill list short and makes activation more precise. The full list is in the [README](./README.md#skills).

---

## Get the pack

```bash
git clone https://github.com/mjs19971997/Claude-Code-Ultimate-Pack.git
```

Windows users who want LF line endings in the working copy can clone with `git clone -c core.autocrlf=false <url>`; this setting applies to this clone only.

Without Git: open <https://github.com/mjs19971997/Claude-Code-Ultimate-Pack>, choose **Code → Download ZIP**, and extract it.

The commands below assume the pack is at `~/Claude-Code-Ultimate-Pack` (Windows: `$HOME\Claude-Code-Ultimate-Pack`). Change `SRC` / `$src` if it is elsewhere.

---

## Install

### Linux, macOS, WSL, Git Bash

```bash
SRC=~/Claude-Code-Ultimate-Pack/skills
DEST=~/.claude/skills            # project install: DEST=/path/to/project/.claude/skills

# All skills, or list only the ones you want, e.g.:
# SKILLS="senior-react-19-engineer nextjs-15-architect typescript-master"
SKILLS=$(ls "$SRC")

mkdir -p "$DEST"
for name in $SKILLS; do
  if [ ! -d "$SRC/$name" ]; then
    echo "not in pack: $name"
  elif [ -e "$DEST/$name" ]; then
    echo "skipped (already exists): $name"
  else
    cp -R "$SRC/$name" "$DEST/$name" && echo "installed: $name"
  fi
done
```

### Windows PowerShell

```powershell
$src  = "$HOME\Claude-Code-Ultimate-Pack\skills"
$dest = "$HOME\.claude\skills"   # project install: $dest = "C:\path\to\project\.claude\skills"

# All skills, or list only the ones you want, e.g.:
# $skills = 'senior-react-19-engineer','nextjs-15-architect','typescript-master'
$skills = (Get-ChildItem $src -Directory).Name

if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }
foreach ($name in $skills) {
    $from = Join-Path $src $name
    $to   = Join-Path $dest $name
    if (-not (Test-Path $from))  { Write-Host "not in pack: $name" }
    elseif (Test-Path $to)       { Write-Host "skipped (already exists): $name" }
    else { Copy-Item -Path $from -Destination $to -Recurse; Write-Host "installed: $name" }
}
```

Claude Code notices new and changed skills during a running session. If the `skills` folder did not exist when the session started, run `/reload-skills` or start a new Claude Code session.

For a project install, commit the copied folders (`.claude/skills/<skill-name>/`) so your team gets the same skills.

---

## Check the install

- In Claude Code, open the `/skills` menu, or ask "What skills are available?".
- Skills load automatically when your request matches their `description`. You can also call one directly by typing `/` followed by its name, for example `/postgresql-expert`.
- Each installed skill folder should contain `SKILL.md` and, for most skills, a `references/` folder:

  ```bash
  ls ~/.claude/skills/postgresql-expert
  ```

To check the pack itself (from the repository root):

```bash
python3 -m pip install pyyaml        # once, if PyYAML is missing
python3 scripts/validate_skills.py   # Windows: py scripts\validate_skills.py
```

The validator only reads files and exits with a non-zero status when it finds an error.

---

## Upgrade

### Updating installed skills

This replaces only the pack's folders that are already installed. Each old folder is first moved into a dated backup folder, so nothing is lost.

```bash
cd ~/Claude-Code-Ultimate-Pack && git pull

SRC=~/Claude-Code-Ultimate-Pack/skills
DEST=~/.claude/skills
BACKUP=~/.claude/skills-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP"
for name in $(ls "$SRC"); do
  if [ -d "$DEST/$name" ]; then
    mv "$DEST/$name" "$BACKUP/$name" && cp -R "$SRC/$name" "$DEST/$name" && echo "updated: $name"
  fi
done
echo "previous versions are in $BACKUP"
```

```powershell
Set-Location "$HOME\Claude-Code-Ultimate-Pack"; git pull

$src    = "$HOME\Claude-Code-Ultimate-Pack\skills"
$dest   = "$HOME\.claude\skills"
$backup = "$HOME\.claude\skills-backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($name in (Get-ChildItem $src -Directory).Name) {
    $to = Join-Path $dest $name
    if (Test-Path $to) {
        Move-Item -Path $to -Destination (Join-Path $backup $name)
        Copy-Item -Path (Join-Path $src $name) -Destination $to -Recurse
        Write-Host "updated: $name"
    }
}
Write-Host "previous versions are in $backup"
```

If you edited a pack skill yourself, compare it with the copy in the backup folder before you delete the backup. To add skills you did not have before, run the [install](#install) commands again; existing folders are skipped.

### From v2.x to v3.0.0

v3.0.0 merges 27 skills into others (93 → 67) and adds one new folder, `android-expert`. The update above refreshes the skills that still exist, but it does not touch folders whose names are no longer in the pack. After updating, remove these old folders yourself if you installed them:

| Old folder (v2.x) | Now part of |
|---|---|
| `software-architect`, `enterprise-architect` | `solution-architect` |
| `schema-org-expert`, `structured-data-expert` | `technical-seo-expert` |
| `cypress-expert` | `e2e-testing-expert` |
| `jest-expert`, `vitest-expert` | `unit-testing-expert` |
| `swiftui-expert`, `uikit-expert` | `swift-expert` |
| `android-architecture-expert`, `android-kotlin-expert`, `jetpack-compose-expert` | `android-expert` (new) |
| `performance-expert` | `core-web-vitals-expert` |
| `performance-optimization-expert` | `scalability-expert` |
| `owasp-top-10-expert` | `secure-coding-expert` |
| `jwt-expert`, `oauth2-expert` | `authentication-expert` |
| `docker-compose-expert` | `docker-expert` |
| `github-actions-expert`, `github-expert` | `cicd-expert` |
| `vector-database-expert` | `rag-expert` |
| `hyperledger-fabric-expert` | `enterprise-blockchain-architect` |
| `multi-agent-expert`, `memory-systems-expert` | `ai-agent-architect` |
| `langgraph-expert` | `langchain-expert` |
| `ubuntu-server-expert` | `linux-expert` |
| `openzeppelin-expert` | `solidity-expert` |

If you used one of the old skills, install its new target with the [install](#install) commands. The old folders can be removed with the same steps as in [Uninstall](#uninstall), using this list of names instead of the current pack:

```text
software-architect enterprise-architect schema-org-expert structured-data-expert
cypress-expert jest-expert vitest-expert swiftui-expert uikit-expert
android-architecture-expert android-kotlin-expert jetpack-compose-expert
performance-expert performance-optimization-expert owasp-top-10-expert
jwt-expert oauth2-expert docker-compose-expert github-actions-expert github-expert
vector-database-expert hyperledger-fabric-expert multi-agent-expert
memory-systems-expert langgraph-expert ubuntu-server-expert openzeppelin-expert
```

---

## Uninstall

Remove only the pack's own folders, by name. The 67 skill names in v3.0.0 are:

```text
accessibility-expert ai-agent-architect android-expert anthropic-sdk-expert
api-security-expert authentication-expert authorization-expert aws-expert
cicd-expert clean-architecture-expert code-review-expert core-web-vitals-expert
crewai-expert dao-expert ddd-expert defi-expert docker-expert e2e-testing-expert
elasticsearch-expert enterprise-blockchain-architect ethereum-expert ethersjs-expert
expressjs-expert foundry-expert framer-motion-expert gemini-sdk-expert git-expert
graphql-expert hardhat-expert integration-testing-expert kubernetes-expert
langchain-expert linux-expert mcp-expert microservices-expert mongodb-expert
nestjs-expert nextjs-15-architect nft-expert nginx-expert nodejs-architect
openai-sdk-expert playwright-expert postgresql-expert prisma-expert
prompt-engineering-expert rag-expert redis-expert refactoring-expert
rest-api-expert scalability-expert secure-coding-expert senior-react-19-engineer
shadcn-ui-expert smart-contract-security-expert solidity-expert solution-architect
swift-expert system-design-expert tailwindcss-master technical-seo-expert
terraform-expert typescript-master ui-designer unit-testing-expert ux-designer
web3js-expert
```

If you also installed skills with these names from another source, leave those out.

### Linux, macOS, WSL, Git Bash

This moves the folders into a dated folder instead of deleting them. Delete that folder later (or move it to the Trash) once you are sure.

```bash
DEST=~/.claude/skills            # project install: DEST=/path/to/project/.claude/skills
NAMES=$(ls ~/Claude-Code-Ultimate-Pack/skills)   # or paste names from the list above
REMOVED=~/.claude/skills-removed-$(date +%Y%m%d-%H%M%S)
mkdir -p "$REMOVED"
for name in $NAMES; do
  if [ -d "$DEST/$name" ]; then
    mv "$DEST/$name" "$REMOVED/$name" && echo "moved: $name"
  fi
done
```

On Linux desktops you can use `gio trash "$DEST/$name"` in the loop instead of `mv` to send each folder to the Trash.

### Windows PowerShell

This sends each folder to the Recycle Bin.

```powershell
$dest  = "$HOME\.claude\skills"   # project install: $dest = "C:\path\to\project\.claude\skills"
$names = (Get-ChildItem "$HOME\Claude-Code-Ultimate-Pack\skills" -Directory).Name   # or a list of names

Add-Type -AssemblyName Microsoft.VisualBasic
foreach ($name in $names) {
    $path = Join-Path $dest $name
    if (Test-Path $path) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($path, 'OnlyErrorDialogs', 'SendToRecycleBin')
        Write-Host "moved to Recycle Bin: $name"
    }
}
```

For a project install, commit the removal in that project as usual. The clone of this repository can be deleted like any other folder.

---

## Troubleshooting

**A skill does not show up.**
Check that the path is `skills/<skill-name>/SKILL.md`, one level deep, and that the folder name matches the `name` field in the frontmatter. If you created the `skills` folder during a session, run `/reload-skills` or start a new Claude Code session.

**A skill does not load when expected.**
Skills are chosen by their `description`. Mention the technology or task the description names, or call the skill directly with `/<skill-name>`. If two skills compete, the "Not for …" clause in each description says which one covers what.

**"Skipped (already exists)" during install.**
A folder with that name is already there, either from an older version of this pack or from somewhere else. Use [Upgrade](#upgrade) for pack folders; otherwise leave it, or rename one of the two.

**YAML or line-ending errors after copying on Windows.**
The files in this repository use LF line endings. If Git converted them, clone again with `git clone -c core.autocrlf=false <url>`.

**Paths with spaces.**
Quote them: `SRC="/path with spaces/Claude-Code-Ultimate-Pack/skills"`.

Questions and bug reports: <https://github.com/mjs19971997/Claude-Code-Ultimate-Pack/issues>
