"""Safe file persistence helpers for JSON write operations."""

from __future__ import annotations

import hashlib
import re
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class FileManagerError(Exception):
    """Raised when a file persistence operation cannot be completed safely."""


class FileManager:
    """Provide safe backup, write, rollback, and conflict-detection primitives."""

    MAX_BACKUPS = 5

    @classmethod
    def backup_file(cls, path: str) -> str:
        """
        Create a numbered backup copy of an existing file.

        Args:
            path: Path to the source file.

        Returns:
            The full path to the backup file.

        Raises:
            FileManagerError: If the source file does not exist.
        """
        source_path = Path(path)
        if not source_path.is_file():
            raise FileManagerError(f"Cannot back up missing file: {path}")

        existing_backups = cls._numbered_backup_paths(source_path)
        next_counter = max((counter for _, counter in existing_backups), default=0) + 1
        backup_path = source_path.with_name(
            f"{source_path.name}.{next_counter:08d}.bak"
        )
        while backup_path.exists():
            next_counter += 1
            backup_path = source_path.with_name(
                f"{source_path.name}.{next_counter:08d}.bak"
            )
        shutil.copy2(source_path, backup_path)
        cls._prune_backups(source_path)
        return str(backup_path)

    @classmethod
    def write_json_safe(cls, path: str, data: Dict[str, Any], create_backup: bool = True) -> None:
        """
        Atomically write JSON data to disk.

        The JSON is written to a temporary file in the destination directory and then
        promoted into place with ``os.replace`` so the target is never half-written.

        Args:
            path: Destination file path.
            data: JSON-serializable dictionary to persist.
            create_backup: When True, create a backup before overwriting an existing file.

        Raises:
            FileManagerError: If the write fails for any reason.
        """
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if create_backup and target_path.exists():
            cls.backup_file(str(target_path))

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(target_path.parent),
                prefix=f"{target_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(data, temp_file, indent=2, ensure_ascii=False)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(str(temp_path), str(target_path))
        except Exception as exc:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
            raise FileManagerError(f"Failed to write JSON safely to {path}: {exc}") from exc

    @classmethod
    def rollback(cls, path: str, backup_path: str) -> None:
        """
        Restore a file from a backup copy using an atomic replace.

        Args:
            path: Destination path to restore.
            backup_path: Backup file to restore from.

        Raises:
            FileManagerError: If the backup file does not exist or restore fails.
        """
        source_backup = Path(backup_path)
        if not source_backup.is_file():
            raise FileManagerError(f"Cannot roll back from missing backup: {backup_path}")

        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(target_path.parent),
                prefix=f"{target_path.name}.",
                suffix=".rollback.tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                with source_backup.open("rb") as backup_file:
                    shutil.copyfileobj(backup_file, temp_file)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(str(temp_path), str(target_path))
        except Exception as exc:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
            raise FileManagerError(
                f"Failed to roll back {path} from backup {backup_path}: {exc}"
            ) from exc

    @staticmethod
    def compute_file_hash(path: str) -> str:
        """
        Return the SHA-256 hex digest for a file's current contents.

        Args:
            path: File path to hash.

        Returns:
            SHA-256 hex digest string.

        Raises:
            FileManagerError: If the file does not exist.
        """
        file_path = Path(path)
        if not file_path.is_file():
            raise FileManagerError(f"Cannot hash missing file: {path}")

        digest = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @classmethod
    def detect_conflict(cls, path: str, expected_hash: Optional[str]) -> bool:
        """
        Detect whether a file changed since an expected hash was recorded.

        Args:
            path: File path to compare.
            expected_hash: Previously recorded hash. If falsy, no conflict check is done.

        Returns:
            True when the current file state does not match ``expected_hash``.
            False when hashes match or when ``expected_hash`` is falsy.
        """
        if not expected_hash:
            return False

        try:
            return cls.compute_file_hash(path) != expected_hash
        except FileManagerError:
            return True

    @classmethod
    def _numbered_backup_paths(cls, source_path: Path) -> list[tuple[Path, int]]:
        """Return this file's numbered backups and their numeric counters."""
        pattern = re.compile(rf"{re.escape(source_path.name)}\.([0-9]+)\.bak\Z")
        backups = []
        for candidate in source_path.parent.iterdir():
            match = pattern.fullmatch(candidate.name)
            if match and candidate.is_file():
                counter = match.group(1)
                # Legacy timestamp backups use a 20-digit ``%Y%m%d%H%M%S%f`` suffix.
                if len(counter) == 20:
                    continue
                backups.append((candidate, int(counter)))
        return backups

    @classmethod
    def _prune_backups(cls, source_path: Path) -> None:
        """Delete older numbered backups so only the newest MAX_BACKUPS remain."""
        backup_paths = cls._numbered_backup_paths(source_path)
        backup_paths.sort(key=lambda item: item[1])

        while len(backup_paths) > cls.MAX_BACKUPS:
            oldest_backup, _ = backup_paths.pop(0)
            oldest_backup.unlink(missing_ok=True)
