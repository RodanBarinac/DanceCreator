"""
FileManager persistence tests.

These tests cover atomic JSON writes, backup retention, rollback, and
optimistic-concurrency hash checks without touching repository data files.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.engine.persistence.FileManager import FileManager, FileManagerError


class TestBackupFile:
    """Test file backup creation and retention behavior."""

    def test_backup_file_creates_timestamped_backup(self, tmp_path):
        """Test that backing up a file creates a .bak copy on disk."""
        source = tmp_path / "dance.json"
        source.write_text('{"Name": "Original"}\n', encoding="utf-8")

        backup_path = Path(FileManager.backup_file(str(source)))

        assert backup_path.exists()
        assert backup_path.suffix == ".bak"
        assert backup_path.name.startswith("dance.json.")

    def test_backup_file_returns_backup_path(self, tmp_path):
        """Test that backup_file returns the created backup path."""
        source = tmp_path / "figure.json"
        source.write_text("{}", encoding="utf-8")

        backup_path = FileManager.backup_file(str(source))

        assert backup_path == str(Path(backup_path))
        assert Path(backup_path).is_file()

    def test_backup_file_preserves_original_content(self, tmp_path):
        """Test that backup content matches the source file content."""
        source = tmp_path / "dance.json"
        original_content = '{\n  "Name": "Source"\n}\n'
        source.write_text(original_content, encoding="utf-8")

        backup_path = Path(FileManager.backup_file(str(source)))

        assert backup_path.read_text(encoding="utf-8") == original_content

    def test_backup_file_does_not_modify_original_file(self, tmp_path):
        """Test that creating a backup leaves the original file unchanged."""
        source = tmp_path / "dance.json"
        source.write_text('{"Version": 1}\n', encoding="utf-8")

        FileManager.backup_file(str(source))

        assert source.read_text(encoding="utf-8") == '{"Version": 1}\n'

    def test_backup_file_raises_for_missing_source(self, tmp_path):
        """Test that backing up a missing file raises FileManagerError."""
        missing = tmp_path / "missing.json"

        with pytest.raises(FileManagerError, match="missing file"):
            FileManager.backup_file(str(missing))

    def test_backup_file_prunes_old_backups_beyond_limit(self, tmp_path):
        """Test that only the newest MAX_BACKUPS backups are retained."""
        source = tmp_path / "dance.json"
        source.write_text('{"Name": "Version 0"}\n', encoding="utf-8")

        created_backups = []
        for index in range(FileManager.MAX_BACKUPS + 2):
            source.write_text(f'{{"Name": "Version {index}"}}\n', encoding="utf-8")
            created_backups.append(Path(FileManager.backup_file(str(source))))

        retained_backups = sorted(tmp_path.glob("dance.json.*.bak"))

        assert len(retained_backups) == FileManager.MAX_BACKUPS
        assert created_backups[0] not in retained_backups
        assert created_backups[1] not in retained_backups
        assert created_backups[-1] in retained_backups


class TestWriteJsonSafe:
    """Test atomic JSON file writes and backup behavior."""

    def test_write_json_safe_creates_new_file(self, tmp_path):
        """Test that write_json_safe creates a new JSON file."""
        target = tmp_path / "new_dance.json"

        FileManager.write_json_safe(str(target), {"Name": "New Dance", "Version": 1})

        assert target.exists()
        assert json.loads(target.read_text(encoding="utf-8")) == {
            "Name": "New Dance",
            "Version": 1,
        }

    def test_write_json_safe_writes_readable_indented_json(self, tmp_path):
        """Test that JSON output is human-readable and uses UTF-8 text."""
        target = tmp_path / "figure.json"

        FileManager.write_json_safe(str(target), {"Name": "Ä figure", "Version": 2})

        contents = target.read_text(encoding="utf-8")
        assert "\n" in contents
        assert '  "Name": "Ä figure"' in contents

    def test_write_json_safe_overwrites_existing_file(self, tmp_path):
        """Test that an existing file is replaced with new JSON content."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Old"}\n', encoding="utf-8")

        FileManager.write_json_safe(str(target), {"Name": "Updated", "Version": 3})

        assert json.loads(target.read_text(encoding="utf-8")) == {
            "Name": "Updated",
            "Version": 3,
        }

    def test_write_json_safe_creates_backup_before_overwrite_by_default(self, tmp_path):
        """Test that overwriting an existing file creates one backup automatically."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Original"}\n', encoding="utf-8")

        FileManager.write_json_safe(str(target), {"Name": "Updated"})

        backups = list(tmp_path.glob("dance.json.*.bak"))
        assert len(backups) == 1
        assert json.loads(backups[0].read_text(encoding="utf-8")) == {"Name": "Original"}

    def test_write_json_safe_skips_backup_for_new_files(self, tmp_path):
        """Test that creating a new file does not create an unnecessary backup."""
        target = tmp_path / "fresh.json"

        FileManager.write_json_safe(str(target), {"Name": "Fresh"})

        assert list(tmp_path.glob("fresh.json.*.bak")) == []

    def test_write_json_safe_skips_backup_when_disabled(self, tmp_path):
        """Test that create_backup=False does not create backup files."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Original"}\n', encoding="utf-8")

        FileManager.write_json_safe(str(target), {"Name": "Updated"}, create_backup=False)

        assert list(tmp_path.glob("dance.json.*.bak")) == []

    def test_write_json_safe_keeps_original_file_when_serialization_fails(self, tmp_path):
        """Test that failed serialization leaves the original file untouched."""
        target = tmp_path / "dance.json"
        original_content = '{"Name": "Original", "Version": 1}\n'
        target.write_text(original_content, encoding="utf-8")

        with pytest.raises(FileManagerError, match="Failed to write JSON safely"):
            FileManager.write_json_safe(str(target), {"bad": {1, 2, 3}})

        assert target.read_text(encoding="utf-8") == original_content

    def test_write_json_safe_does_not_create_target_when_serialization_fails(self, tmp_path):
        """Test that failed writes do not leave a new target file behind."""
        target = tmp_path / "dance.json"

        with pytest.raises(FileManagerError):
            FileManager.write_json_safe(str(target), {"bad": object()})

        assert not target.exists()

    def test_write_json_safe_cleans_up_temp_file_on_failure(self, tmp_path):
        """Test that temp files are removed when JSON serialization fails."""
        target = tmp_path / "dance.json"

        with pytest.raises(FileManagerError):
            FileManager.write_json_safe(str(target), {"bad": object()})

        assert list(tmp_path.glob("dance.json.*.tmp")) == []

    def test_write_json_safe_creates_parent_directory(self, tmp_path):
        """Test that missing parent directories are created automatically."""
        target = tmp_path / "nested" / "folder" / "dance.json"

        FileManager.write_json_safe(str(target), {"Name": "Nested"})

        assert target.exists()
        assert target.parent.is_dir()


class TestRollback:
    """Test restoring files from backups."""

    def test_rollback_restores_previous_content(self, tmp_path):
        """Test that rollback replaces current content with backup content."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Original"}\n', encoding="utf-8")
        backup_path = Path(FileManager.backup_file(str(target)))
        target.write_text('{"Name": "Changed"}\n', encoding="utf-8")

        FileManager.rollback(str(target), str(backup_path))

        assert json.loads(target.read_text(encoding="utf-8")) == {"Name": "Original"}

    def test_rollback_can_restore_missing_target_from_backup(self, tmp_path):
        """Test that rollback recreates the target file when only backup exists."""
        target = tmp_path / "dance.json"
        backup = tmp_path / "dance.json.20260101010101000000.bak"
        backup.write_text('{"Name": "Recovered"}\n', encoding="utf-8")

        FileManager.rollback(str(target), str(backup))

        assert json.loads(target.read_text(encoding="utf-8")) == {"Name": "Recovered"}

    def test_rollback_raises_for_missing_backup(self, tmp_path):
        """Test that rollback fails clearly when the backup file is missing."""
        target = tmp_path / "dance.json"
        missing_backup = tmp_path / "missing.bak"

        with pytest.raises(FileManagerError, match="missing backup"):
            FileManager.rollback(str(target), str(missing_backup))


class TestComputeFileHash:
    """Test deterministic file hashing behavior."""

    def test_compute_file_hash_is_deterministic_across_calls(self, tmp_path):
        """Test that repeated hashing of the same file returns the same digest."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Stable"}\n', encoding="utf-8")

        first_hash = FileManager.compute_file_hash(str(target))
        second_hash = FileManager.compute_file_hash(str(target))

        assert first_hash == second_hash

    def test_compute_file_hash_matches_for_same_content(self, tmp_path):
        """Test that separate files with the same content produce the same hash."""
        first = tmp_path / "one.json"
        second = tmp_path / "two.json"
        contents = '{"Name": "Same"}\n'
        first.write_text(contents, encoding="utf-8")
        second.write_text(contents, encoding="utf-8")

        assert FileManager.compute_file_hash(str(first)) == FileManager.compute_file_hash(str(second))

    def test_compute_file_hash_differs_for_different_content(self, tmp_path):
        """Test that different file content yields different hashes."""
        first = tmp_path / "one.json"
        second = tmp_path / "two.json"
        first.write_text('{"Name": "One"}\n', encoding="utf-8")
        second.write_text('{"Name": "Two"}\n', encoding="utf-8")

        assert FileManager.compute_file_hash(str(first)) != FileManager.compute_file_hash(str(second))

    def test_compute_file_hash_raises_for_missing_file(self, tmp_path):
        """Test that hashing a missing file raises FileManagerError."""
        missing = tmp_path / "missing.json"

        with pytest.raises(FileManagerError, match="missing file"):
            FileManager.compute_file_hash(str(missing))


class TestDetectConflict:
    """Test optimistic-concurrency conflict detection."""

    def test_detect_conflict_returns_false_when_hash_matches(self, tmp_path):
        """Test that no conflict is reported when the file is unchanged."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Stable"}\n', encoding="utf-8")
        expected_hash = FileManager.compute_file_hash(str(target))

        assert FileManager.detect_conflict(str(target), expected_hash) is False

    def test_detect_conflict_returns_true_when_file_changes(self, tmp_path):
        """Test that modified file content is reported as a conflict."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Before"}\n', encoding="utf-8")
        expected_hash = FileManager.compute_file_hash(str(target))
        target.write_text('{"Name": "After"}\n', encoding="utf-8")

        assert FileManager.detect_conflict(str(target), expected_hash) is True

    def test_detect_conflict_returns_false_when_expected_hash_is_none(self, tmp_path):
        """Test that None disables conflict detection."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Stable"}\n', encoding="utf-8")

        assert FileManager.detect_conflict(str(target), None) is False

    def test_detect_conflict_returns_false_when_expected_hash_is_empty(self, tmp_path):
        """Test that empty hash values disable conflict detection."""
        target = tmp_path / "dance.json"
        target.write_text('{"Name": "Stable"}\n', encoding="utf-8")

        assert FileManager.detect_conflict(str(target), "") is False

    def test_detect_conflict_returns_true_when_file_is_missing(self, tmp_path):
        """Test that a missing file counts as a conflict when hash checking is requested."""
        missing = tmp_path / "missing.json"

        assert FileManager.detect_conflict(str(missing), "expected-hash") is True
