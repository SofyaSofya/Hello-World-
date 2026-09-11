"""Loads family_roles.json (the astrological ruleset shared with the rest of the project)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_ROLES_PATH = REPO_ROOT / "family_roles.json"


@lru_cache(maxsize=1)
def load_family_roles() -> dict:
    with FAMILY_ROLES_PATH.open() as f:
        return json.load(f)


def get_aspect_orb_rules() -> dict:
    return load_family_roles()["planetary_thread_rules"]
