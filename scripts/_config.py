#!/usr/bin/env python3
"""Shared config loader for all scripts in this repository.

Business parameters live in exactly one place: `config/config.json` in the
repository root. If that file does not exist yet (a fresh checkout, or the
operator has not run onboarding), `config/config.example.json` is used so
the scripts still run against the fictional example values.

Usage from other scripts in this directory:

    import _config
    cfg = _config.load()                      # full dict (cached)
    cap = _config.get("daily_send_cap", 30)   # one key with a fallback

Command-line arguments in each script override config values; config
values override the example file. Nothing business-specific is hard-coded
in any script.

Importing this module also loads the repo-root `.env` file (if present)
into the environment without overriding variables already set, so secrets
the operator stored there reach every script. See `_load_dotenv`.
"""
import json
import os

_CACHE = None


def repo_root():
    """Repository root = parent directory of this scripts/ folder."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_dotenv(path):
    """Parse a simple KEY=VALUE .env file. Returns a dict ({} if unreadable)."""
    values = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key.startswith("export "):
                    key = key[len("export "):].strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                if key:
                    values[key] = value
    except OSError:
        pass
    return values


def _load_dotenv():
    """Load the repo-root .env into os.environ, never overriding real env vars.

    This is the one supported place for the operator's secrets on a local
    machine: the executing agent writes the credentials the operator hands
    over into `<repo>/.env` (git-ignored, never committed, never printed),
    and every script picks them up from there. A variable already set in
    the real environment always wins over the file.
    """
    path = os.path.join(repo_root(), ".env")
    for key, value in _parse_dotenv(path).items():
        os.environ.setdefault(key, value)


_load_dotenv()


def config_path():
    """Prefer the operator's real config; fall back to the example file."""
    root = repo_root()
    real = os.path.join(root, "config", "config.json")
    if os.path.exists(real):
        return real
    return os.path.join(root, "config", "config.example.json")


def load():
    """Return the config dict, loaded once and cached."""
    global _CACHE
    if _CACHE is None:
        path = config_path()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                _CACHE = json.load(fh)
        else:
            _CACHE = {}
    return _CACHE


def get(key, default=None):
    """One config value, or `default` when the key is absent."""
    return load().get(key, default)


def data_path(name):
    """Absolute path of a file inside the repository's data/ folder."""
    return os.path.join(repo_root(), "data", name)


if __name__ == "__main__":
    print(f"config file in use: {config_path()}")
    print(json.dumps(load(), ensure_ascii=False, indent=2))
