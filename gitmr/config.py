import os

from dotenv import load_dotenv

# Repo root when running from a source checkout (parent of gitmr/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _user_config_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "git-mr")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return os.path.join(xdg, "git-mr")
    return os.path.join(os.path.expanduser("~"), ".config", "git-mr")


def user_env_path() -> str:
    return os.path.join(_user_config_dir(), ".env")


def _env_files_to_load():
    """Order: user config first, then repo .env overrides (dev checkout)."""
    explicit = os.getenv("GITMR_ENV", "").strip()
    if explicit:
        return [explicit]

    paths = []
    user_env = user_env_path()
    if os.path.isfile(user_env):
        paths.append(user_env)

    repo_env = os.path.join(_REPO_ROOT, ".env")
    if os.path.isfile(repo_env):
        paths.append(repo_env)

    return paths


def _load_env():
    paths = _env_files_to_load()
    for i, path in enumerate(paths):
        load_dotenv(path, override=(i > 0))


def _env_bool(name, default=False):
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "y", "on")


def load_config():
    _load_env()

    config = {
        "gitlab_url": os.getenv("GITLAB_URL", "").strip(),
        "gitlab_token": os.getenv("GITLAB_TOKEN", "").strip(),
        "project_id": os.getenv("GITLAB_PROJECT_ID", "").strip(),
        "project_path": os.getenv("GITLAB_PROJECT_PATH", "").strip(),
        "git_remote": os.getenv("GITLAB_GIT_REMOTE", "origin").strip() or "origin",
        "default_target": os.getenv("GITLAB_DEFAULT_TARGET", "develop").strip(),
        "openai_api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "auto_ai": _env_bool("GITMR_AUTO_AI", True),
        "default_assignee_id": os.getenv("GITMR_DEFAULT_ASSIGNEE_ID", "").strip(),
    }

    _validate(config)
    return config


def _validate(config):
    required = ["gitlab_url", "gitlab_token"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        user_env = user_env_path()
        raise ValueError(
            f"Missing required env: {', '.join(missing)}. "
            f"Create {user_env} (see .env.example) or set GITMR_ENV to your config file."
        )
