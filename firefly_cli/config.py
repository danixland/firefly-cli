# Copyright (C) 2026 Danilo M. <danix@danix.xyz>  GPL-2.0-only
import os
import tomllib
from pathlib import Path
from firefly_cli.errors import ConfigError

DEFAULT_PATH = Path(os.path.expanduser("~/.config/firefly-cli/config.toml"))

def load(path=DEFAULT_PATH, env=None):
    env = os.environ if env is None else env
    url = env.get("FIREFLY_URL")
    token = env.get("FIREFLY_TOKEN")
    if not (url and token) and Path(path).exists():
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        url = url or data.get("url")
        token = token or data.get("token")
    if not url or not token:
        raise ConfigError(
            "No Firefly III config found. Run `firefly auth set` "
            "or set FIREFLY_URL and FIREFLY_TOKEN."
        )
    return {"url": url.rstrip("/"), "token": token}

def write(url, token, path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # tomllib cannot write; template the 2-key file (deps stay at zero).
    content = (
        f'url = "{url.rstrip("/")}"\n'
        f'token = "{token}"\n'
    )
    path.write_text(content)
    path.chmod(0o600)
    return path
