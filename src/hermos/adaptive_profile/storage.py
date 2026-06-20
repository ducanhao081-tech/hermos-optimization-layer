"""Explicit, local JSON persistence for preference profiles."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from .models import PreferenceProfile


class JsonProfileStore:
    """Store profiles below a host-selected directory.

    No home-directory path is assumed. User identifiers are hashed before they
    become filenames, preventing path traversal and reducing identifier leakage.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path_for(self, user_id: str) -> Path:
        if not user_id.strip():
            raise ValueError("user_id must not be empty")
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def load(self, user_id: str) -> Optional[PreferenceProfile]:
        path = self.path_for(user_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = PreferenceProfile.from_dict(data)
        if profile.user_id != user_id:
            raise ValueError("stored profile does not match requested user_id")
        return profile

    def load_or_create(self, user_id: str) -> PreferenceProfile:
        return self.load(user_id) or PreferenceProfile(user_id=user_id)

    def save(self, profile: PreferenceProfile) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.path_for(profile.user_id)
        payload = json.dumps(profile.to_dict(), ensure_ascii=False, indent=2) + "\n"
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=str(self.root),
            prefix=".profile-",
            suffix=".tmp",
            text=True,
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        finally:
            temporary_path = Path(temporary_name)
            if temporary_path.exists():
                temporary_path.unlink()
        return destination

    def delete(self, user_id: str) -> bool:
        path = self.path_for(user_id)
        if not path.exists():
            return False
        path.unlink()
        return True
