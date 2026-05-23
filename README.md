# git-mr

Interactive CLI to create GitLab merge requests from your terminal. It detects the project from your git remote, shows branch diffs, optionally drafts title and description with OpenAI, and creates the MR on GitLab.

## Workflows

| Menu | Flow |
|------|------|
| **1** | Current branch → `develop` (feature MR) |
| **2** | `develop` → `staging` (promotion) |
| **3** | `staging` → `master` (production promotion) |

## Install (recommended)

Install once so `git-mr` is available on your PATH:

```bash
cd git-mr-tool
pip install -e .
```

Or with [pipx](https://pipx.pypa.io/) (isolated, no venv needed):

```bash
pipx install /path/to/git-mr-tool
# upgrade after pulling changes:
pipx install --force /path/to/git-mr-tool
```

From a git URL (team install):

```bash
pipx install git+https://your-gitlab.com/team/git-mr-tool.git
```

Then run from **any** project repo:

```bash
git-mr
```

## Config (one file for all your repos)

Copy `.env.example` to your user config directory:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\git-mr\.env` |
| Linux / macOS | `~/.config/git-mr/.env` |

Or set `GITMR_ENV` to point at any `.env` file.

```env
GITLAB_URL=http://your-gitlab-host
GITLAB_TOKEN=glpat-xxxxxxxx
GITLAB_DEFAULT_TARGET=develop
OPENAI_API_KEY=sk-...           # optional; enables AI drafts

# Project auto-detected from git remote — no per-repo ID needed.
# GITLAB_PROJECT_PATH=group/subgroup/repo
# GITLAB_PROJECT_ID=123
# GITMR_AUTO_AI=true
# GITMR_DEFAULT_ASSIGNEE_ID=42
```

When developing this repo, a `.env` in the project root overrides the user file.

## Development setup

```bash
cd git-mr-tool
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .
copy .env.example .env          # local override for dev
```

## Usage

Run from **inside** the git repository you are working on:

```bash
git-mr
```

Alternatives:

```bash
python -m gitmr
python cli.py
```

### Review screen

- **Enter** — create MR
- **e** — edit title and description in the terminal
- **g** — regenerate AI content
- **a** — pick assignee
- **r** — add reviewer
- **q** — quit

## Project layout

```
git-mr-tool/
  pyproject.toml      # package + git-mr command
  .env.example
  cli.py              # optional launcher
  README.md
  gitmr/
    cli.py            # entry: git-mr
    config.py
    gitlab.py
    workflows.py
    wizard.py
    content.py
    ui.py
```

## Requirements

- Python 3.10+
- Git on `PATH`
- GitLab token with `api` scope
- OpenAI API key (optional)
