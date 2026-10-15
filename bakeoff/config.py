"""Load and validate bake-off configs (YAML)."""
from __future__ import annotations
import pathlib, yaml

SUITES = {"vision", "voice", "agent"}
REQUIRED_MODEL_KEYS = {"tag"}


class ConfigError(ValueError):
    pass


def load(path) -> dict:
    p = pathlib.Path(path)
    cfg = yaml.safe_load(p.read_text())
    return validate(cfg, base=p.parent)


def validate(cfg: dict, base=None) -> dict:
    if not isinstance(cfg, dict):
        raise ConfigError("config must be a mapping")
    cfg.setdefault("ollama_url", "http://127.0.0.1:11434")
    cfg.setdefault("seed", 42)
    if not isinstance(cfg["seed"], int):
        raise ConfigError("seed must be an int")
    models = cfg.get("models")
    if not models:
        raise ConfigError("models: at least one model required")
    for m in models:
        missing = REQUIRED_MODEL_KEYS - set(m)
        if missing:
            raise ConfigError(f"model missing keys {missing}: {m}")
        if ":" not in m["tag"] or m["tag"].endswith(":latest"):
            raise ConfigError(f"model tag must be pinned (name:size, not :latest): {m['tag']}")
    suites = cfg.get("suites") or {}
    unknown = set(suites) - SUITES
    if unknown:
        raise ConfigError(f"unknown suites {unknown}")
    if base is not None:
        for name, s in suites.items():
            f = s.get("file")
            if f:
                s["data"] = yaml.safe_load((pathlib.Path(base) / f).read_text())
    return cfg
