# Installation Guide

This guide covers every supported installation method for the Claude Code Ultimate Pack. Choose the method that matches your workflow.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
   - [Method 1: Global Installation (Recommended)](#method-1-global-installation-recommended)
   - [Method 2: Project-Local Installation](#method-2-project-local-installation)
   - [Method 3: Selective Installation](#method-3-selective-installation)
   - [Method 4: Git Submodule](#method-4-git-submodule)
   - [Method 5: Symlink for Development](#method-5-symlink-for-development)
3. [Verification](#verification)
4. [Updating](#updating)
5. [Uninstalling](#uninstalling)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before installing, ensure you have:

- **Claude Code CLI** installed and configured (version 1.0.0 or later)
- **Git** for cloning the repository
- **Bash** or **Zsh** shell (Windows users: use WSL2 or Git Bash)
- **~50 MB** of free disk space for the full pack
- A working `~/.claude/` directory (created automatically by Claude Code on first run)

To verify Claude Code is installed:

```bash
claude --version
```

If this command fails, install Claude Code first per the official Anthropic documentation.

---

## Installation Methods

### Method 1: Global Installation (Recommended)

Global installation makes every skill available in every project on your machine. This is the recommended method for individual developers who want the full pack available at all times.

```bash
# 1. Clone the repository to a permanent location
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git ~/claude-code-ultimate-pack

# 2. Create the global skills directory if it does not exist
mkdir -p ~/.claude/skills

# 3. Copy all skills into the global skills directory
cp -r ~/claude-code-ultimate-pack/skills/* ~/.claude/skills/

# 4. Verify installation
ls ~/.claude/skills/
```

Expected output:

```
ai          architecture  backend  blockchain  database
devops      frontend      mobile   security    seo  testing
```

### Method 2: Project-Local Installation

Project-local installation makes skills available only within a specific project. This is the recommended method for teams who want to version-control their skill selection alongside project code.

```bash
# 1. Navigate to your project root
cd /path/to/your/project

# 2. Initialize Claude Code configuration if not already present
mkdir -p .claude/skills

# 3. Clone the pack into a temporary location
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git /tmp/ultimate-pack

# 4. Copy the skills you want (or all of them)
cp -r /tmp/ultimate-pack/skills/* .claude/skills/

# 5. Clean up the temporary clone
rm -rf /tmp/ultimate-pack

# 6. Commit the skills to your project repository
git add .claude/skills/
git commit -m "chore: add Claude Code Ultimate Pack skills"
```

### Method 3: Selective Installation

If you only need a subset of domains, install selectively to keep your environment lean.

```bash
# Clone the repository
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git /tmp/ultimate-pack

# Create the skills directory
mkdir -p ~/.claude/skills

# Install only the domains you need
cp -r /tmp/ultimate-pack/skills/frontend ~/.claude/skills/
cp -r /tmp/ultimate-pack/skills/backend ~/.claude/skills/
cp -r /tmp/ultimate-pack/skills/database ~/.claude/skills/

# Or install a single skill
cp /tmp/ultimate-pack/skills/ai/prompt-engineering-expert.md ~/.claude/skills/
```

### Method 4: Git Submodule

For teams that want to track the upstream pack while keeping it isolated from project code:

```bash
# From your project root
git submodule add https://github.com/your-org/Claude-Code-Ultimate-Pack.git .claude/ultimate-pack

# Symlink the skills directory so Claude Code discovers them
ln -s .claude/ultimate-pack/skills .claude/skills

# Commit the submodule
git add .gitmodules .claude/ultimate-pack
git commit -m "chore: add Claude Code Ultimate Pack as submodule"
```

To update later:

```bash
git submodule update --remote .claude/ultimate-pack
git add .claude/ultimate-pack
git commit -m "chore: update Claude Code Ultimate Pack"
```

### Method 5: Symlink for Development

If you are contributing to the pack and want your changes to be picked up instantly:

```bash
# Clone the repository to your development location
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git ~/projects/claude-code-ultimate-pack

# Symlink each domain into your global skills directory
mkdir -p ~/.claude/skills
for domain in frontend backend database blockchain mobile devops architecture security testing ai seo; do
  ln -s ~/projects/claude-code-ultimate-pack/skills/$domain ~/.claude/skills/$domain
done
```

Now any edit you make in `~/projects/claude-code-ultimate-pack/skills/` is immediately available to Claude Code.

---

## Verification

After installation, verify that Claude Code recognizes the skills:

```bash
# List all installed skills
claude skills list
```

You should see output similar to:

```
Domain        Skill Count  Status
-----------   ----------   ------
ai            14           active
architecture  8            active
backend       10           active
blockchain    13           active
database      5            active
devops        13           active
frontend      10           active
mobile        6            active
security      5            active
seo           4            active
testing       7            active
-----------   ----------   ------
Total         95           active
```

To test a specific skill:

```bash
claude "Using the senior-react-19-engineer skill, write a useDebounce hook"
```

Claude Code should respond using the conventions, patterns, and standards defined in `senior-react-19-engineer.md`.

---

## Updating

### Global installation

```bash
cd ~/claude-code-ultimate-pack
git pull origin main
cp -r skills/* ~/.claude/skills/
```

### Project-local installation

```bash
cd /tmp
git clone https://github.com/your-org/Claude-Code-Ultimate-Pack.git
cp -r Claude-Code-Ultimate-Pack/skills/* /path/to/your/project/.claude/skills/
cd /path/to/your/project
git add .claude/skills/
git commit -m "chore: update Claude Code Ultimate Pack"
```

### Submodule

```bash
git submodule update --remote .claude/ultimate-pack
git add .claude/ultimate-pack
git commit -m "chore: update Claude Code Ultimate Pack"
```

---

## Uninstalling

### Global

```bash
rm -rf ~/.claude/skills/frontend ~/.claude/skills/backend ~/.claude/skills/database
rm -rf ~/.claude/skills/blockchain ~/.claude/skills/mobile ~/.claude/skills/devops
rm -rf ~/.claude/skills/architecture ~/.claude/skills/security ~/.claude/skills/testing
rm -rf ~/.claude/skills/ai ~/.claude/skills/seo
rm -rf ~/claude-code-ultimate-pack
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

## Troubleshooting

### Skills not appearing in `claude skills list`

1. Verify the files are in the correct directory:
   ```bash
   ls ~/.claude/skills/frontend/
   ```
   You should see `.md` files like `senior-react-19-engineer.md`.

2. Verify file permissions:
   ```bash
   chmod -R 644 ~/.claude/skills/**/*.md
   ```

3. Restart Claude Code:
   ```bash
   claude restart
   ```

### Skill not activating when expected

Claude Code activates skills based on context. If a skill does not activate, invoke it explicitly:

```bash
claude "@nestjs-expert Design a module for user authentication"
```

### Conflicting skills from other packs

If you have other skill packs installed, conflicts may occur. Remove the conflicting packs:

```bash
# List all installed skills
ls ~/.claude/skills/

# Remove any non-Ultimate-Pack skills
rm -rf ~/.claude/skills/old-pack-name
```

### File paths with spaces

If your home directory contains spaces, quote all paths:

```bash
cp -r "/path with spaces/Claude-Code-Ultimate-Pack/skills/"* "$HOME/.claude/skills/"
```

### Windows (WSL2) specific issues

Ensure line endings are LF, not CRLF:

```bash
# In WSL2
find ~/.claude/skills -name "*.md" -exec dos2unix {} \;
```

If `dos2unix` is not installed:

```bash
sudo apt install dos2unix
```

---

For further assistance, open an issue at:
`https://github.com/your-org/Claude-Code-Ultimate-Pack/issues`
