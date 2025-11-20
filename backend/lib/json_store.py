"""Lightweight JSON-backed storage with atomic writes.

This module provides a minimal persistence helper for the MVP JSON database.
It keeps the implementation synchronous and dependency-free while ensuring
durable writes via a temporary-file-and-rename strategy instead of OS locks.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Callable, Tuple

Mutator = Callable[[Any], Tuple[Any, Any]]


class JsonStore:
    """Provide read/update helpers for a JSON document on disk.

    Files are stored next to the FastAPI app and written atomically by serialising
    into a temporary file before renaming it into place. No OS-level lock files are
    used so the helper stays portable across Linux, macOS, and Windows.
    """

    def __init__(self, path: os.PathLike[str] | str, default_factory: Callable[[], Any]):
        self.path = Path(path)
        self.default_factory = default_factory

        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self._write_unlocked(self.default_factory())

    def _read_unlocked(self) -> Any:
        if not self.path.exists():
            data = self.default_factory()
            self._write_unlocked(data)
            return data

        with open(self.path, "r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                # Reset the file if the contents are corrupt.
                data = self.default_factory()
                self._write_unlocked(data)
                return data

    def _write_unlocked(self, data: Any) -> None:
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as tmp_handle:
            json.dump(data, tmp_handle, indent=2, ensure_ascii=True)
            tmp_handle.flush()
            os.fsync(tmp_handle.fileno())
        tmp_path.replace(self.path)

    def read(self) -> Any:
        """Return a deep copy of the stored JSON document."""
        data = self._read_unlocked()
        return copy.deepcopy(data)

    def write(self, data: Any) -> None:
        """Persist ``data`` to disk atomically."""
        self._write_unlocked(data)

    def update(self, mutator: Mutator) -> Any:
        """Load, mutate, persist, and return an arbitrary result.

        The ``mutator`` receives the *current* document and must return a tuple of
        ``(new_document, result)``. This keeps the helper generic enough for
        higher-level repositories to manipulate the payload while still getting a
        meaningful return value.
        """
        current = self._read_unlocked()
        new_document, result = mutator(current)
        self._write_unlocked(new_document)
        return result


__all__ = ["JsonStore"]
