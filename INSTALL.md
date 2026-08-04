# Installation Guide

This guide covers every supported installation method for the Claude Code Ultimate Pack v2.0 on **Windows**, **Linux**, and **macOS**. v2.0 uses the official [Claude Code Agent Skills specification](https://code.claude.com/docs/en/skills) — each skill is a folder containing a `SKILL.md` file with YAML frontmatter.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Platform-Specific Instructions](#platform-specific-instructions)
   - [Windows](#windows)
   - [Linux](#linux)
   - [macOS](#macos)
4. [Global Installation](#global-installation)
5. [Project-Local Installation](#project-local-installation)
6. [Manual Installation](#manual-installation)
7. [Selective Installation](#selective-installation)
8. [Git Submodule](#git-submodule)
9. [Upgrade](#upgrade)
10. [Validation](#validation)
11. [Common Errors](#common-errors)
12. [Troubleshooting](#troubleshooting)
13. [Uninstalling](#uninstalling)

---

## Prerequisites

Before installing, ensure you have:

- **Claude Code** installed and configured (version 1.0.0 or later). Verify with:
  ```bash
  claude --version
  ```
  If this command fails, install Claude Code first per the [official Anthropic documentation](https://code.claude.com/docs/en).
- **Git** for cloning the repository.
- A working `~/.claude/` directory (created automatically by Claude Code on first run).
- ~50 MB of free disk space for the full pack (93 skills × ~50 KB average).

### Platform notes

| Platform | Shell | Notes |
|---|---|---|
| Windows 10/11 | PowerShell 5+ or PowerShell 7+ | Use PowerShell commands below. WSL2 also works — see [WSL2 notes](#wsl2-notes). |
| Windows 10/11 | WSL2 (Ubuntu) | Use the Linux commands. |
| Linux | Bash or Zsh | Use the Linux commands. |
| macOS | Zsh (default since Catalina) or Bash | Use the macOS commands. |

---

## Quick Start

One-liner per platform:

### Linux / macOS / WSL2

```bash
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git \
  && mkdir -p ~/.claude/skills \
  && cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/ \
  && claude restart
```

### Windows (PowerShell)

```powershell
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git `
  ; New-Item -ItemType Directory -Force -Path $HOME\.claude\skills | Out-Null `
  ; Copy-Item -Path Claude-Code-Ultimate-Pack\skills\* -Destination $HOME\.claude\skills\ -Recurse `
  ; claude restart
```

---

## Platform-Specific Instructions

### Windows

#### Option A — Native Windows (PowerShell)

1. **Open PowerShell** (Press `Win + X`, then click "Windows PowerShell" or "Terminal").

2. **Verify Claude Code is installed**:
   ```powershell
   claude --version
   ```

3. **Clone the repository**:
   ```powershell
   cd $HOME
   git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
   ```

4. **Create the skills directory** (Claude Code may not create it until first launch):
   ```powershell
   New-Item -ItemType Directory -Force -Path $HOME\.claude\skills | Out-Null
   ```

5. **Copy all skills** — each skill is a folder, so use `-Recurse`:
   ```powershell
   Copy-Item -Path Claude-Code-Ultimate-Pack\skills\* `
             -Destination $HOME\.claude\skills\ `
             -Recurse -Force
   ```

6. **Verify**:
   ```powershell
   Get-ChildItem $HOME\.claude\skills -Directory | Measure-Object | Select-Object -ExpandProperty Count
   # Expected: 93
   ```

7. **Restart Claude Code**:
   ```powershell
   claude restart
   ```

#### Option B — WSL2 (Ubuntu)

If you use Claude Code inside WSL2, follow the [Linux](#linux) instructions instead. Your Claude Code skills directory is `~/.claude/skills/` **inside the WSL2 filesystem** (e.g., `/home/<user>/.claude/skills/`), not the Windows-side path.

To copy from the Windows-side download into WSL2:

```bash
# Inside WSL2
cp -r /mnt/c/Users/<YourWindowsUser>/Downloads/Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
```

##### WSL2 notes

- **Line endings**: if you cloned on the Windows side and copied into WSL2, files may have CRLF endings. Convert to LF:
  ```bash
  sudo apt install dos2unix -y
  find ~/.claude/skills -name "SKILL.md" -exec dos2unix {} \;
  ```
- **Symlinks**: WSL2 symlinks to Windows-side paths work but may be slow. For performance, keep the skills inside the WSL2 filesystem.

#### Option C — Git Bash (Windows)

If you prefer Git Bash, the Linux commands work, but paths use the Unix form:

```bash
cd ~
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
mkdir -p ~/.claude/skills
cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
```

### Linux

Tested on Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch Linux, and Alpine Linux.

1. **Open a terminal**.

2. **Verify Claude Code is installed**:
   ```bash
   claude --version
   ```

3. **Clone the repository**:
   ```bash
   cd ~
   git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
   ```

4. **Create the skills directory**:
   ```bash
   mkdir -p ~/.claude/skills
   ```

5. **Copy all skills** — each skill is a folder, so use `-r`:
   ```bash
   cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
   ```

6. **Verify**:
   ```bash
   ls ~/.claude/skills/ | wc -l
   # Expected: 93
   ```

7. **Restart Claude Code**:
   ```bash
   claude restart
   ```

#### Linux distro-specific notes

- **Snap-installed Claude Code**: snap packages sandbox `~/.claude/`. If you installed Claude Code via snap, use `~/snap/claude/current/.claude/skills/` instead.
- **Flatpak-installed Claude Code**: use `~/.var/app/com.anthropic.Claude/.claude/skills/`.
- **Headless servers**: skills work the same way — Claude Code reads `~/.claude/skills/` regardless of whether a GUI is present.

### macOS

Tested on macOS 12 Monterey through macOS 15 Sequoia, both Intel and Apple Silicon.

1. **Open Terminal** (Press `Cmd + Space`, type "Terminal", press Enter).

2. **Verify Claude Code is installed**:
   ```bash
   claude --version
   ```

3. **Clone the repository**:
   ```bash
   cd ~
   git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
   ```

4. **Create the skills directory**:
   ```bash
   mkdir -p ~/.claude/skills
   ```

5. **Copy all skills**:
   ```bash
   cp -R Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
   ```

6. **Verify**:
   ```bash
   ls ~/.claude/skills/ | wc -l
   # Expected: 93
   ```

7. **Restart Claude Code**:
   ```bash
   claude restart
   ```

#### macOS-specific notes

- **`cp -R` vs `cp -r`**: On macOS, `cp -R` (uppercase) is the BSD form that preserves directory structure. Both work, but `cp -R` is canonical on macOS.
- **iCloud-synced home directory**: if your `~/Library` is synced to iCloud, `~/.claude/` may not be. Verify with `ls -la ~/.claude/` — if it's a symlink to iCloud, skills may sync slowly across devices. To disable, move `~/.claude` out of the iCloud-synced hierarchy.
- **Gatekeeper**: macOS Gatekeeper does not block plain text/markdown files, so no quarantine steps are needed.

---

## Global Installation

Global installation makes every skill available in every project on your machine. This is the recommended method for individual developers.

The platform-specific instructions above ([Windows](#windows), [Linux](#linux), [macOS](#macos)) all install globally — they copy `skills/*` into `~/.claude/skills/`.

To verify a global install:

```bash
# Linux / macOS
ls -d ~/.claude/skills/*/ | wc -l
# Expected: 93

# Windows PowerShell
(Get-ChildItem $HOME\.claude\skills -Directory).Count
# Expected: 93
```

---

## Project-Local Installation

Project-local installation makes skills available only within a specific project. This is the recommended method for teams who want to version-control their skill selection alongside project code.

### Linux / macOS / WSL2

```bash
cd /path/to/your/project

# Initialize Claude Code config
mkdir -p .claude/skills

# Copy the skills you want (or all of them)
cp -r /path/to/Claude-Code-Ultimate-Pack/skills/* .claude/skills/

# Commit to your project repository
git add .claude/skills/
git commit -m "chore: add Claude Code Ultimate Pack v2.0 skills"
```

### Windows (PowerShell)

```powershell
cd C:\path\to\your\project

# Initialize Claude Code config
New-Item -ItemType Directory -Force -Path .claude\skills | Out-Null

# Copy the skills
Copy-Item -Path C:\path\to\Claude-Code-Ultimate-Pack\skills\* `
          -Destination .claude\skills\ `
          -Recurse

# Commit to your project repository
git add .claude\skills\
git commit -m "chore: add Claude Code Ultimate Pack v2.0 skills"
```

Project-local skills take precedence over global skills of the same name. This is useful for pinning a specific version of a skill per project.

---

## Manual Installation

If you cannot or do not want to use `git clone`, you can install manually from a downloaded zip.

### Step 1: Download the zip

Download `Claude-Code-Ultimate-Pack.zip` from the [releases page](https://github.com/your-org/Claude-Code-Ultimate-Pack/releases).

### Step 2: Extract

#### Linux / macOS

```bash
cd ~
unzip Claude-Code-Ultimate-Pack.zip
```

#### Windows

Right-click the zip → "Extract All…" → choose destination → click "Extract".

Or in PowerShell:

```powershell
Expand-Archive -Path Claude-Code-Ultimate-Pack.zip -DestinationPath $HOME
```

### Step 3: Copy skills

#### Linux / macOS

```bash
mkdir -p ~/.claude/skills
cp -r Claude-Code-Ultimate-Pack/skills/* ~/.claude/skills/
```

#### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force -Path $HOME\.claude\skills | Out-Null
Copy-Item -Path $HOME\Claude-Code-Ultimate-Pack\skills\* `
          -Destination $HOME\.claude\skills\ `
          -Recurse
```

### Step 4: Restart Claude Code

```bash
claude restart
```

---

## Selective Installation

If you only need a subset of skills, install selectively to keep your environment lean.

### Linux / macOS

```bash
# List available skills
ls Claude-Code-Ultimate-Pack/skills/

# Install specific skills by name
mkdir -p ~/.claude/skills
for skill in senior-react-19-engineer nextjs-15-architect typescript-master; do
  cp -r Claude-Code-Ultimate-Pack/skills/$skill ~/.claude/skills/
done
```

### Windows (PowerShell)

```powershell
# List available skills
Get-ChildItem Claude-Code-Ultimate-Pack\skills\ -Directory | Select-Object -ExpandProperty Name

# Install specific skills
$skills = 'senior-react-19-engineer','nextjs-15-architect','typescript-master'
foreach ($s in $skills) {
    Copy-Item -Path "Claude-Code-Ultimate-Pack\skills\$s" `
              -Destination $HOME\.claude\skills\ `
              -Recurse
}
```

### Install by domain

The v2.0 layout is flat, but you can install all skills in a domain by referencing the [skill index](./docs/skill-index.md). For example, to install all AI skills:

```bash
# Linux / macOS
ai_skills="ai-agent-architect mcp-expert langgraph-expert langchain-expert crewai-expert openai-sdk-expert anthropic-sdk-expert gemini-sdk-expert prompt-engineering-expert rag-expert vector-database-expert memory-systems-expert multi-agent-expert"
for s in $ai_skills; do
  cp -r Claude-Code-Ultimate-Pack/skills/$s ~/.claude/skills/
done
```

---

## Git Submodule

For teams that want to track the upstream pack while keeping it isolated from project code:

```bash
# From your project root
git submodule add https://github.com/your-org/Claude-Code-Ultimate-Pack.git .claude/ultimate-pack

# Symlink the skills directory so Claude Code discovers them
ln -s .claude/ultimate-pack/skills .claude/skills

# Commit the submodule
git add .gitmodules .claude/ultimate-pack .claude/skills
git commit -m "chore: add Claude Code Ultimate Pack v2.0 as submodule"
```

**Windows note**: symbolic links on Windows require either Developer Mode (Windows 10 1703+) or running PowerShell as Administrator. Alternative — copy instead of symlink:

```powershell
git submodule add https://github.com/your-org/Claude-Code-Ultimate-Pack.git .claude\ultimate-pack
Copy-Item -Path .claude\ultimate-pack\skills\* -Destination .claude\skills\ -Recurse
git add .gitmodules .claude\ultimate-pack .claude\skills
git commit -m "chore: add Claude Code Ultimate Pack v2.0 as submodule"
```

---

## Upgrade

### From v1.x to v2.0 (breaking migration)

v1.x used `skills/<domain>/<skill-name>.md`. v2.0 uses `skills/<skill-name>/SKILL.md`. You **must** remove the old install before installing v2.0:

#### Linux / macOS / WSL2

```bash
# 1. Remove the 11 legacy domain folders
rm -rf ~/.claude/skills/{ai,architecture,backend,blockchain,database,devops,frontend,mobile,security,seo,testing}

# 2. Pull v2.0
cd ~/Claude-Code-Ultimate-Pack
git pull origin main
git checkout v2.0.0   # or 'main' if you prefer the latest

# 3. Install v2.0
cp -r skills/* ~/.claude/skills/

# 4. Restart
claude restart

# 5. Verify
ls ~/.claude/skills/ | wc -l   # Expected: 93
```

#### Windows (PowerShell)

```powershell
# 1. Remove the 11 legacy domain folders
$domains = 'ai','architecture','backend','blockchain','database','devops','frontend','mobile','security','seo','testing'
foreach ($d in $domains) {
    Remove-Item -Recurse -Force "$HOME\.claude\skills\$d" -ErrorAction SilentlyContinue
}

# 2. Pull v2.0
cd $HOME\Claude-Code-Ultimate-Pack
git pull origin main
git checkout v2.0.0

# 3. Install v2.0
Copy-Item -Path skills\* -Destination $HOME\.claude\skills\ -Recurse

# 4. Restart
claude restart

# 5. Verify
(Get-ChildItem $HOME\.claude\skills -Directory).Count   # Expected: 93
```

### Patch upgrade within v2.x

```bash
# Linux / macOS
cd ~/Claude-Code-Ultimate-Pack
git pull origin main
# Replace existing skills (folder-by-folder so deletes propagate)
rsync -a --delete skills/ ~/.claude/skills/
claude restart
```

```powershell
# Windows
cd $HOME\Claude-Code-Ultimate-Pack
git pull origin main
Remove-Item -Recurse -Force $HOME\.claude\skills\*
Copy-Item -Path skills\* -Destination $HOME\.claude\skills\ -Recurse
claude restart
```

### Submodule upgrade

```bash
git submodule update --remote .claude/ultimate-pack
git add .claude/ultimate-pack
git commit -m "chore: update Claude Code Ultimate Pack to latest v2.x"
```

---

## Validation

After installation, validate that every skill is correctly structured:

### Using the bundled validator

```bash
# Linux / macOS — requires Python 3.9+ and PyYAML
pip install pyyaml
python3 /path/to/Claude-Code-Ultimate-Pack/scripts/validate_skills.py
```

Expected output:

```
Validation report written to: validation-report.json
Total skills:    93
Skills passed:   93
Skills w/ errors: 0
Repo checks:     4/4
Overall pass:    True
```

### Manual spot-check

```bash
# 1. Count skill folders
ls ~/.claude/skills/ | wc -l   # Expected: 93

# 2. Verify one skill's structure
head -10 ~/.claude/skills/senior-react-19-engineer/SKILL.md
# Should start with '---' and have name/description/license/version

# 3. Verify YAML parses
python3 -c "import yaml; print(yaml.safe_load(open('$HOME/.claude/skills/senior-react-19-engineer/SKILL.md').read().split('---')[1]))"
# Should print a dict with name, description, license, version
```

### Windows PowerShell spot-check

```powershell
# 1. Count skill folders
(Get-ChildItem $HOME\.claude\skills -Directory).Count   # Expected: 93

# 2. Verify one skill's structure
Get-Content $HOME\.claude\skills\senior-react-19-engineer\SKILL.md -Head 10
# Should start with '---' and have name/description/license/version
```

---

## Common Errors

### Error: "Skill folder missing SKILL.md"

**Cause**: You copied the contents of `skills/` directly into `~/.claude/skills/` without preserving the per-skill folder structure.

**Fix**: Re-copy using `-r` (Linux/macOS) or `-Recurse` (Windows):

```bash
# Linux / macOS — WRONG:
cp skills/* ~/.claude/skills/   # This flattens the structure

# Linux / macOS — CORRECT:
cp -r skills/* ~/.claude/skills/   # Each skill becomes a folder
```

### Error: "YAML parse error in SKILL.md"

**Cause**: The frontmatter is malformed — usually a missing closing `---`, an unescaped `:` in the description, or CRLF line endings.

**Fix**:

1. Verify the file starts with `---\n` (no BOM, no leading blank line).
2. Verify there's a second `---` line closing the frontmatter.
3. Convert CRLF to LF (Windows):
   ```bash
   # WSL2 or Git Bash
   find ~/.claude/skills -name "SKILL.md" -exec dos2unix {} \;
   ```
4. Re-validate with the [validator](#validation).

### Error: "Skill name 'Foo_Bar' is invalid"

**Cause**: The `name` field in YAML frontmatter doesn't match the spec (lowercase letters, digits, hyphens only; max 64 chars).

**Fix**: Rename the folder and update the `name` field. The folder name and the `name` field must be identical.

### Error: "Skill not auto-activating"

**Cause**: Claude Code couldn't match your prompt to any skill's `description` field.

**Fix**:

1. Invoke the skill explicitly:
   ```
   /skill senior-react-19-engineer
   Build a useDebounce hook
   ```
2. If it still doesn't activate, check that the skill folder is at `~/.claude/skills/<skill-name>/SKILL.md` (not nested deeper).
3. Restart Claude Code.

### Error: "Permission denied" when copying to `~/.claude/skills/`

**Cause**: The `~/.claude/` directory is owned by another user or has restrictive permissions.

**Fix**:

```bash
# Linux / macOS
sudo chown -R $(whoami) ~/.claude
chmod -R u+rwX ~/.claude
```

### Error: "claude: command not found"

**Cause**: Claude Code CLI is not installed or not on your `PATH`.

**Fix**: Install Claude Code per the [official documentation](https://code.claude.com/docs/en). On Windows, ensure `claude.exe` is in your `PATH` (the installer does this automatically; restart your terminal after install).

---

## Troubleshooting

### Skills not appearing after install

1. Verify each skill is a folder containing `SKILL.md`:
   ```bash
   # Linux / macOS
   ls ~/.claude/skills/senior-react-19-engineer/
   # Should print: SKILL.md
   ```
2. Verify the YAML frontmatter:
   ```bash
   head -10 ~/.claude/skills/senior-react-19-engineer/SKILL.md
   ```
3. Check file permissions:
   ```bash
   # Linux / macOS
   chmod -R u+rwX ~/.claude/skills
   ```
4. Restart Claude Code:
   ```bash
   claude restart
   ```

### Conflicting skills from other packs

If you have other skill packs installed, conflicts may occur. Remove the conflicting packs:

```bash
# Linux / macOS
# List all installed skills
ls ~/.claude/skills/

# Remove any non-Ultimate-Pack skills
rm -rf ~/.claude/skills/old-pack-skill-name
```

### File paths with spaces

If your home directory or clone location contains spaces, quote all paths:

```bash
# Linux / macOS
cp -r "/path with spaces/Claude-Code-Ultimate-Pack/skills/"* "$HOME/.claude/skills/"
```

```powershell
# Windows
Copy-Item -Path "C:\path with spaces\Claude-Code-Ultimate-Pack\skills\*" `
          -Destination "$HOME\.claude\skills\" `
          -Recurse
```

### Symlink issues (Linux / macOS)

If you used the symlink-for-development method and symlinks are broken:

```bash
# Remove broken symlinks
find ~/.claude/skills -maxdepth 1 -type l ! -exec test -e {} \; -delete

# Re-create
ln -s /path/to/Claude-Code-Ultimate-Pack/skills/<skill-name> ~/.claude/skills/<skill-name>
```

### Windows Defender blocking scripts

If Windows Defender SmartScreen blocks Claude Code from reading skill files:

1. Open "Windows Security" → "App & browser control" → "SmartScreen for Explorer".
2. Add `~/.claude/` to the excluded locations.
3. Restart Claude Code.

### macOS quarantine attribute

If macOS marks cloned files as quarantined (rare for plain markdown, but possible):

```bash
xattr -dr com.apple.quarantine ~/Claude-Code-Ultimate-Pack
```

---

## Uninstalling

### Global

```bash
# Linux / macOS — remove all 93 skill folders
rm -rf ~/.claude/skills

# Or selectively
rm -rf ~/.claude/skills/senior-react-19-engineer
# ... repeat for each skill

# Optionally remove the clone
rm -rf ~/Claude-Code-Ultimate-Pack
```

```powershell
# Windows
Remove-Item -Recurse -Force $HOME\.claude\skills
# Or selectively
Remove-Item -Recurse -Force $HOME\.claude\skills\senior-react-19-engineer
```

### Project-local

```bash
cd /path/to/your/project
rm -rf .claude/skills
git add -A
git commit -m "chore: remove Claude Code Ultimate Pack"
```

### Submodule

```bash
git submodule deinit -f .claude/ultimate-pack
git rm -f .claude/ultimate-pack
rm -rf .git/modules/.claude/ultimate-pack
git commit -m "chore: remove Claude Code Ultimate Pack submodule"
```

---

For further assistance, open an issue at:
`https://github.com/your-org/Claude-Code-Ultimate-Pack/issues`
