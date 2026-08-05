import os
from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    env_root = os.getenv("SPARKHUB_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parent


PROJECT_ROOT = get_project_root()


def get_path(*parts: Union[str, os.PathLike[str]]) -> Path:
    return PROJECT_ROOT.joinpath(*[str(part) for part in parts])


def get_default_port(default_port: int = 8000) -> int:
    raw_value = os.getenv("SPARKHUB_PORT", str(default_port)).strip()
    try:
        return int(raw_value)
    except ValueError:
        return default_port
