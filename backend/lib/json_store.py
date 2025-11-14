"""Lightweight JSON-backed storage with cooperative file locking.

This module provides a minimal persistence helper for the MVP JSON database.
It keeps the implementation synchronous and dependency-free while ensuring
atomic writes via an adjacent ``.lock`` file and ``fcntl`` advisory locking.
"""

from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Tuple

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError as exc:  # pragma: no cover - Linux-only in this project
    raise RuntimeError("POSIX fcntl module required for file locking") from exc

Mutator = Callable[[Any], Tuple[Any, Any]]


class JsonStore:
    """Provide guarded read/update access to a JSON file on disk.

    The store keeps a sibling ``*.lock`` file that acts as a mutex via ``fcntl``.
    Reads and writes go through that lock to avoid concurrent corruption when the
    FastAPI app (or tests) touch the store from multiple tasks.
    """

    def __init__(self, path: os.PathLike[str] | str, default_factory: Callable[[], Any]):
        self.path = Path(path)
        self.default_factory = default_factory
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)

        if not self.path.exists():
            self._write_unlocked(self.default_factory())

    @contextmanager
    def _locked(self):
        with open(self.lock_path, "w", encoding="utf-8") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle, fcntl.LOCK_UN)

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
        with self._locked():
            data = self._read_unlocked()
            return copy.deepcopy(data)

    def write(self, data: Any) -> None:
        """Persist ``data`` to disk atomically."""
        with self._locked():
            self._write_unlocked(data)

    def update(self, mutator: Mutator) -> Any:
        """Lock, load, mutate, persist, and return an arbitrary result.

        The ``mutator`` receives the *current* document and must return a tuple of
        ``(new_document, result)``.  This keeps the helper generic enough for
        higher-level repositories to manipulate the payload however they like
        while still getting a meaningful return value.
        """
        with self._locked():
            current = self._read_unlocked()
            new_document, result = mutator(current)
            self._write_unlocked(new_document)
            return result


__all__ = ["JsonStore"]
