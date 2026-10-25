"""Portable, validated dance archives and transactional per-dance storage."""

from __future__ import annotations

import errno
import io
import json
import os
import re
import shutil
import threading
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping
from uuid import uuid4

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
)
from src.engine.domain.legacy_adapter import LegacyDanceAdapter
from src.engine.figures.capabilities import FigureRepository
from src.engine.figures.addon_utils import duration_addon_bars


CURRENT_FORMAT_VERSION = 1
_MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
_MAX_MEMBER_BYTES = 64 * 1024 * 1024
_MAX_TOTAL_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
_MAX_MEMBER_COUNT = 512
_MAX_COMPRESSION_RATIO = 1000
_MAX_DANCE_TREE_DEPTH = 128
_READ_CHUNK_BYTES = 64 * 1024
_STORE_LOCKS: dict[str, Any] = {}
_STORE_LOCKS_GUARD = threading.Lock()


class ArchiveError(ValueError):
    """An archive is malformed, unsupported, or semantically inconsistent."""


class ArchiveCollisionError(ArchiveError):
    """An import would overwrite an existing dance without explicit consent."""


class ArchiveNotFoundError(ArchiveError):
    """A stored dance ID does not exist."""


class ArchiveTransactionError(ArchiveError):
    """An archive could not be promoted without compromising stored data."""


@dataclass(frozen=True)
class ArchivePackage:
    package_id: str
    dance_name: str
    document: DanceDocument
    figures: Mapping[str, dict[str, Any]]
    assets: Mapping[str, bytes]
    incomplete: bool
    manifest: Mapping[str, Any]
    figure_bytes: Mapping[str, bytes]

    @property
    def executable(self) -> bool:
        return not self.incomplete


@dataclass(frozen=True)
class ImportedDance:
    dance_id: str
    document: DanceDocument
    path: Path
    repository: FigureRepository
    package_id: str


def export_archive(
    document: DanceDocument,
    repository: FigureRepository,
    destination: str | Path,
    *,
    assets: Mapping[str, bytes] | None = None,
    package_id: str | None = None,
) -> Path:
    """Write one deterministic ZIP package (apart from its default unique ID)."""
    if not isinstance(document, DanceDocument):
        raise ArchiveError("dance.json: expected a canonical DanceDocument")
    if not isinstance(repository, FigureRepository):
        if not all(
            callable(getattr(repository, method, None))
            for method in ("get_legacy_definition", "get_definition")
        ):
            raise ArchiveError("figure repository must provide legacy and capability definitions")

    figures: dict[str, dict[str, Any]] = {}
    unresolved = set(document.unresolved_references)
    pending = sorted(_document_references(document) - unresolved)
    while pending:
        figure_ref = pending.pop(0)
        if figure_ref in figures or figure_ref in unresolved:
            continue
        _validate_figure_ref(figure_ref, "dance.json")
        try:
            definition = repository.get_legacy_definition(figure_ref)
        except (FileNotFoundError, KeyError) as error:
            raise ArchiveError(
                f"dance.json: referenced figure {figure_ref!r} has no definition"
            ) from error
        except (OSError, ValueError, TypeError) as error:
            raise ArchiveError(
                f"figures/{figure_ref}.json: invalid definition: {error}"
            ) from error
        if not isinstance(definition, dict):
            raise ArchiveError(f"figures/{figure_ref}.json: definition must be an object")
        figures[figure_ref] = definition
        if definition.get("Version") == 3:
            try:
                composite_document = LegacyDanceAdapter.from_data(
                    definition,
                    lambda ref: True,
                )
            except (ValueError, TypeError) as error:
                raise ArchiveError(
                    f"figures/{figure_ref}.json: malformed composite definition: {error}"
                ) from error
            pending.extend(
                sorted(_document_references(composite_document) - set(pending) - set(figures))
            )

    figure_bytes = {
        reference: _json_bytes(definition)
        for reference, definition in sorted(figures.items())
    }
    asset_bytes: dict[str, bytes] = {}
    for member, content in (assets or {}).items():
        _validate_member_path(member, "assets/")
        if not isinstance(content, bytes):
            raise ArchiveError(f"{member}: asset content must be bytes")
        asset_bytes[member] = content

    manifest = {
        "formatVersion": CURRENT_FORMAT_VERSION,
        "packageId": package_id if package_id is not None else str(uuid4()),
        "danceName": _dance_name(document),
        "figures": {
            reference: f"figures/{reference}.json"
            for reference in sorted(figures)
        },
        "incomplete": document.incomplete,
    }
    if not isinstance(manifest["packageId"], str) or not manifest["packageId"].strip():
        raise ArchiveError("package.json: packageId must be a non-empty string")

    _validate_content(
        manifest,
        document.to_json(),
        figure_bytes,
        asset_bytes,
    )

    destination = Path(destination)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ArchiveTransactionError(
            f"Could not prepare archive destination {destination}: {error}"
        ) from error
    staged = destination.with_name(f".{destination.name}.{uuid4().hex}.staging")
    try:
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_zip_member(archive, "package.json", _json_bytes(manifest))
            _write_zip_member(archive, "dance.json", _json_bytes(document.to_json()))
            for reference, content in sorted(figure_bytes.items()):
                _write_zip_member(archive, f"figures/{reference}.json", content)
            for member, content in sorted(asset_bytes.items()):
                _write_zip_member(archive, member, content)
        _validate_written_archive(staged)
        os.replace(staged, destination)
    except ArchiveError:
        staged.unlink(missing_ok=True)
        raise
    except OSError as error:
        staged.unlink(missing_ok=True)
        raise ArchiveTransactionError(f"Could not write archive {destination}: {error}") from error
    except zipfile.BadZipFile as error:
        staged.unlink(missing_ok=True)
        raise ArchiveTransactionError(f"Could not write archive {destination}: {error}") from error
    return destination


def export_archive_bytes(
    document: DanceDocument,
    repository: FigureRepository,
    *,
    assets: Mapping[str, bytes] | None = None,
    package_id: str | None = None,
) -> bytes:
    """Build a validated archive in memory without staging files."""
    if not isinstance(document, DanceDocument):
        raise ArchiveError("dance.json: expected a canonical DanceDocument")
    if not isinstance(repository, FigureRepository) and not all(
        callable(getattr(repository, method, None))
        for method in ("get_legacy_definition", "get_definition")
    ):
        raise ArchiveError("figure repository must provide legacy and capability definitions")

    figures: dict[str, dict[str, Any]] = {}
    unresolved = set(document.unresolved_references)
    pending = sorted(_document_references(document) - unresolved)
    while pending:
        figure_ref = pending.pop(0)
        if figure_ref in figures or figure_ref in unresolved:
            continue
        _validate_figure_ref(figure_ref, "dance.json")
        try:
            definition = repository.get_legacy_definition(figure_ref)
        except (FileNotFoundError, KeyError) as error:
            raise ArchiveError(
                f"dance.json: referenced figure {figure_ref!r} has no definition"
            ) from error
        except (OSError, ValueError, TypeError) as error:
            raise ArchiveError(
                f"figures/{figure_ref}.json: invalid definition: {error}"
            ) from error
        if not isinstance(definition, dict):
            raise ArchiveError(f"figures/{figure_ref}.json: definition must be an object")
        figures[figure_ref] = definition
        if definition.get("Version") == 3:
            try:
                composite_document = LegacyDanceAdapter.from_data(
                    definition,
                    lambda ref: True,
                )
            except (ValueError, TypeError) as error:
                raise ArchiveError(
                    f"figures/{figure_ref}.json: malformed composite definition: {error}"
                ) from error
            pending.extend(
                sorted(_document_references(composite_document) - set(pending) - set(figures))
            )

    figure_bytes = {
        reference: _json_bytes(definition)
        for reference, definition in sorted(figures.items())
    }
    asset_bytes: dict[str, bytes] = {}
    for member, content in (assets or {}).items():
        _validate_member_path(member, "assets/")
        if not isinstance(content, bytes):
            raise ArchiveError(f"{member}: asset content must be bytes")
        asset_bytes[member] = content

    manifest = {
        "formatVersion": CURRENT_FORMAT_VERSION,
        "packageId": package_id if package_id is not None else str(uuid4()),
        "danceName": _dance_name(document),
        "figures": {reference: f"figures/{reference}.json" for reference in sorted(figures)},
        "incomplete": document.incomplete,
    }
    if not isinstance(manifest["packageId"], str) or not manifest["packageId"].strip():
        raise ArchiveError("package.json: packageId must be a non-empty string")
    _validate_content(manifest, document.to_json(), figure_bytes, asset_bytes)

    result = io.BytesIO()
    try:
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            _write_zip_member(archive, "package.json", _json_bytes(manifest))
            _write_zip_member(archive, "dance.json", _json_bytes(document.to_json()))
            for reference, content in sorted(figure_bytes.items()):
                _write_zip_member(archive, f"figures/{reference}.json", content)
            for member, content in sorted(asset_bytes.items()):
                _write_zip_member(archive, member, content)
    except (OSError, zipfile.BadZipFile) as error:
        raise ArchiveTransactionError(f"Could not build archive in memory: {error}") from error
    output = result.getvalue()
    validate_archive(output)
    return output


def validate_archive(source: str | Path | bytes | bytearray | io.BytesIO) -> ArchivePackage:
    """Read and validate all package members entirely in memory."""
    try:
        source_size = _archive_source_size(source)
        if source_size is not None and source_size > _MAX_ARCHIVE_BYTES:
            raise ArchiveError(
                f"package: compressed archive size exceeds {_MAX_ARCHIVE_BYTES} bytes"
            )
        archive_source = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
        with zipfile.ZipFile(archive_source, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            _validate_archive_names(names)
            _validate_archive_info_limits(infos)
            members: dict[str, bytes] = {}
            total_size = 0
            for info in infos:
                content = _read_archive_member(archive, info, total_size)
                members[info.filename] = content
                total_size += len(content)
    except ArchiveError:
        raise
    except (
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
        NotImplementedError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ) as error:
        raise ArchiveError(f"package: cannot read ZIP archive: {error}") from error
    except KeyError as error:
        raise ArchiveError(f"package: missing member {error}") from error

    return _validate_package_members(members)


def _validate_package_members(members: Mapping[str, bytes]) -> ArchivePackage:
    _validate_in_memory_member_limits(members)
    try:
        return _validate_package_members_impl(members)
    except RecursionError as error:
        raise ArchiveError("package: nested content exceeds supported validation depth") from error


def _validate_package_members_impl(members: Mapping[str, bytes]) -> ArchivePackage:
    if "package.json" not in members:
        raise ArchiveError("package.json: required manifest member is missing")
    if "dance.json" not in members:
        raise ArchiveError("dance.json: required canonical dance member is missing")
    manifest = _decode_json(members["package.json"], "package.json")
    dance_json = _decode_json(members["dance.json"], "dance.json")
    figure_members = {
        name: content
        for name, content in members.items()
        if name.startswith("figures/")
    }
    assets = {
        name: content
        for name, content in members.items()
        if name.startswith("assets/")
    }

    if not isinstance(manifest, dict):
        raise ArchiveError("package.json: manifest must be an object")
    expected_keys = {"formatVersion", "packageId", "danceName", "figures", "incomplete"}
    if set(manifest) != expected_keys:
        raise ArchiveError(
            "package.json: manifest fields must be exactly "
            f"{sorted(expected_keys)} (got {sorted(manifest)})"
        )
    version = manifest["formatVersion"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != CURRENT_FORMAT_VERSION
    ):
        raise ArchiveError(
            f"package.json.formatVersion: unsupported version {version!r}; "
            f"current version is {CURRENT_FORMAT_VERSION}"
        )
    package_id = manifest["packageId"]
    if not isinstance(package_id, str) or not package_id.strip():
        raise ArchiveError("package.json.packageId: expected a non-empty string")
    dance_name = manifest["danceName"]
    if not isinstance(dance_name, str) or not dance_name.strip():
        raise ArchiveError("package.json.danceName: expected a non-empty string")
    incomplete = manifest["incomplete"]
    if not isinstance(incomplete, bool):
        raise ArchiveError("package.json.incomplete: expected a boolean")
    figure_map = manifest["figures"]
    if not isinstance(figure_map, dict):
        raise ArchiveError("package.json.figures: expected a reference-to-member object")

    if (
        not isinstance(dance_json, dict)
        or isinstance(dance_json.get("formatVersion"), bool)
        or not isinstance(dance_json.get("formatVersion"), int)
    ):
        raise ArchiveError("dance.json.formatVersion: expected the current integer version")
    _validate_dance_tree_depth(dance_json.get("root"))
    try:
        document = DanceDocument.from_json(dance_json)
    except (TypeError, ValueError, KeyError) as error:
        raise ArchiveError(f"dance.json: invalid canonical tree: {error}") from error
    if incomplete != document.incomplete:
        raise ArchiveError(
            "package.json.incomplete: incomplete/unresolved-reference status does not "
            "match dance.json status"
        )
    if dance_name != _dance_name(document):
        raise ArchiveError(
            f"package.json.danceName: {dance_name!r} does not match dance.json metadata"
        )

    expected_member_names: set[str] = set()
    figure_bytes: dict[str, bytes] = {}
    for reference, member in figure_map.items():
        _validate_figure_ref(reference, "package.json.figures")
        expected_member = f"figures/{reference}.json"
        if member != expected_member:
            raise ArchiveError(
                f"package.json.figures[{reference!r}]: expected member {expected_member!r}"
            )
        expected_member_names.add(expected_member)
        if expected_member not in figure_members:
            raise ArchiveError(f"{expected_member}: referenced definition is missing")
        figure_bytes[reference] = figure_members[expected_member]
    unexpected_figures = set(figure_members) - expected_member_names
    missing_figures = expected_member_names - set(figure_members)
    if unexpected_figures:
        raise ArchiveError(
            f"{sorted(unexpected_figures)[0]}: extra figure member/reference "
            "not declared in package.json"
        )
    if missing_figures:
        raise ArchiveError(f"{sorted(missing_figures)[0]}: required figure member is missing")
    other_members = set(members) - {"package.json", "dance.json"} - expected_member_names - set(assets)
    if other_members:
        raise ArchiveError(f"{sorted(other_members)[0]}: unexpected package member")

    figures: dict[str, dict[str, Any]] = {}
    for reference, content in figure_bytes.items():
        definition = _decode_json(content, f"figures/{reference}.json")
        if not isinstance(definition, dict):
            raise ArchiveError(f"figures/{reference}.json: definition must be an object")
        figures[reference] = definition
    _validate_package_semantics(document, figures)
    return ArchivePackage(
        package_id=package_id,
        dance_name=dance_name,
        document=document,
        figures=figures,
        assets=assets,
        incomplete=incomplete,
        manifest=manifest,
        figure_bytes=figure_bytes,
    )


def _validate_dance_tree_depth(root: Any) -> None:
    pending = [(root, 1)]
    while pending:
        node, depth = pending.pop()
        if depth > _MAX_DANCE_TREE_DEPTH:
            raise ArchiveError(
                "dance.json: nesting depth exceeds "
                f"{_MAX_DANCE_TREE_DEPTH} levels"
            )
        if not isinstance(node, dict):
            continue
        if node.get("type") == "group":
            children = node.get("children")
            if isinstance(children, list):
                pending.extend((child, depth + 1) for child in children)
        elif node.get("type") == "compositeOccurrence":
            pending.append((node.get("root"), depth + 1))


def _archive_source_size(source: Any) -> int | None:
    if isinstance(source, (bytes, bytearray)):
        return len(source)
    if isinstance(source, (str, Path)):
        return Path(source).stat().st_size
    if isinstance(source, io.BytesIO):
        return source.getbuffer().nbytes
    return None


def _validate_archive_info_limits(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > _MAX_MEMBER_COUNT:
        raise ArchiveError(f"package: member count exceeds {_MAX_MEMBER_COUNT}")
    total_size = 0
    for info in infos:
        if info.file_size < 0 or info.file_size > _MAX_MEMBER_BYTES:
            raise ArchiveError(
                f"{info.filename}: uncompressed member size exceeds {_MAX_MEMBER_BYTES} bytes"
            )
        total_size += info.file_size
        if total_size > _MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ArchiveError(
                "package: total uncompressed size exceeds "
                f"{_MAX_TOTAL_UNCOMPRESSED_BYTES} bytes"
            )
        if (
            info.file_size
            > max(1, info.compress_size) * _MAX_COMPRESSION_RATIO
        ):
            raise ArchiveError(
                f"{info.filename}: compression ratio exceeds {_MAX_COMPRESSION_RATIO}:1"
            )


def _read_archive_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    total_size: int,
) -> bytes:
    remaining_total = _MAX_TOTAL_UNCOMPRESSED_BYTES - total_size
    limit = min(_MAX_MEMBER_BYTES, remaining_total)
    content = bytearray()
    with archive.open(info, "r") as member:
        while True:
            chunk = member.read(min(_READ_CHUNK_BYTES, limit - len(content) + 1))
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > limit:
                raise ArchiveError(
                    f"{info.filename}: actual uncompressed data exceeds package limits"
                )
    if len(content) > max(1, info.compress_size) * _MAX_COMPRESSION_RATIO:
        raise ArchiveError(
            f"{info.filename}: actual compression ratio exceeds {_MAX_COMPRESSION_RATIO}:1"
        )
    return bytes(content)


def _store_thread_lock(root: Path):
    key = os.path.normcase(str(root.resolve()))
    with _STORE_LOCKS_GUARD:
        return _STORE_LOCKS.setdefault(key, threading.RLock())


@contextmanager
def _exclusive_store_lock(root: Path):
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ArchiveTransactionError(
            f"Could not lock archive store {root}: {error}"
        ) from error
    with _store_thread_lock(root):
        try:
            lock_file = (root / ".archive-store.lock").open("a+b")
        except OSError as error:
            raise ArchiveTransactionError(
                f"Could not open archive store lock for {root}: {error}"
            ) from error
        with lock_file:
            _acquire_store_file_lock(lock_file, root)
            try:
                yield
            finally:
                _release_store_file_lock(lock_file, root)


def _acquire_store_file_lock(lock_file, root: Path) -> None:
    try:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        lock_file.seek(0)
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in (
                        errno.EACCES,
                        errno.EDEADLK,
                        errno.EAGAIN,
                    ):
                        raise
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    except OSError as error:
        raise ArchiveTransactionError(
            f"Could not acquire archive store lock for {root}: {error}"
        ) from error


def _release_store_file_lock(lock_file, root: Path) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError as error:
        raise ArchiveTransactionError(
            f"Could not release archive store lock for {root}: {error}"
        ) from error


def _validate_in_memory_member_limits(members: Mapping[str, bytes]) -> None:
    names = list(members)
    _validate_archive_names(names)
    if len(names) > _MAX_MEMBER_COUNT:
        raise ArchiveError(f"package: member count exceeds {_MAX_MEMBER_COUNT}")
    total_size = 0
    for name, content in members.items():
        if not isinstance(content, bytes):
            raise ArchiveError(f"{name}: member content must be bytes")
        if len(content) > _MAX_MEMBER_BYTES:
            raise ArchiveError(
                f"{name}: uncompressed member size exceeds {_MAX_MEMBER_BYTES} bytes"
            )
        total_size += len(content)
        if total_size > _MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ArchiveError(
                "package: total uncompressed size exceeds "
                f"{_MAX_TOTAL_UNCOMPRESSED_BYTES} bytes"
            )


class ArchiveStore:
    """Transactional, per-dance package store with isolated figure repositories."""

    def __init__(
        self,
        root: str | Path,
        *,
        shared_figure_directory: str | Path | None = None,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.dances_directory = self.root / "dances"
        self.backups_directory = self.root / "backups"
        self.shared_figure_directory = (
            Path(shared_figure_directory).resolve()
            if shared_figure_directory is not None
            else None
        )
        self.failure_injector = failure_injector

    def import_archive(
        self,
        source: str | Path | bytes | bytearray | io.BytesIO,
        *,
        collision: str = "copy",
        confirm_replace: bool = False,
        copy_name: str | None = None,
        target_name: str | None = None,
        expected_revision: int | None = None,
        replacement_revision: int | None = None,
        target_id: str | None = None,
    ) -> ImportedDance:
        package = validate_archive(source)
        if target_name is not None:
            if not isinstance(target_name, str) or not target_name.strip():
                raise ArchiveError("target_name must be a non-empty dance name")
            package = _rename_package(package, target_name)
        if target_id is not None:
            if collision != "replace":
                raise ArchiveError("target_id is only valid when collision='replace'")
            _validate_store_id(target_id)
        with _exclusive_store_lock(self.root):
            return self._import_package(
                package,
                collision=collision,
                confirm_replace=confirm_replace,
                copy_name=copy_name,
                expected_revision=expected_revision,
                replacement_revision=replacement_revision,
                target_id=target_id,
            )

    def _import_package(
        self,
        package: ArchivePackage,
        *,
        collision: str,
        confirm_replace: bool,
        copy_name: str | None,
        expected_revision: int | None,
        replacement_revision: int | None,
        target_id: str | None,
    ) -> ImportedDance:
        if collision not in ("copy", "replace"):
            raise ArchiveError("collision must be either 'copy' or 'replace'")
        if replacement_revision is not None and expected_revision is None:
            raise ArchiveError(
                "replacement_revision requires an expected target revision"
            )

        if target_id is None:
            existing = self._find_by_name(package.dance_name)
        else:
            existing = self.dances_directory / target_id
            if not existing.is_dir():
                raise ArchiveCollisionError(
                    "Replacement target does not exist; replacement was not applied"
                )
            conflicting_name = self._find_by_name(package.dance_name)
            if conflicting_name is not None and conflicting_name != existing:
                raise ArchiveCollisionError(
                    f"Dance name {package.dance_name!r} already exists"
                )
        replacing = existing is not None and collision == "replace"
        if replacement_revision is not None and not replacing:
            raise ArchiveError(
                "replacement_revision is only valid when replacing an existing dance"
            )
        if collision == "replace" and existing is None and expected_revision is not None:
            raise ArchiveCollisionError(
                "Replacement target does not exist; replacement was not applied"
            )
        if collision == "replace":
            if copy_name is not None:
                raise ArchiveError("copy_name is only valid when collision='copy'")
            if existing is not None and not confirm_replace:
                raise ArchiveCollisionError(
                    f"Dance {package.dance_name!r} already exists; replace requires confirmation"
                )
            if existing is not None:
                existing_package = _validate_package_directory(existing)
                if expected_revision is not None:
                    if (
                        isinstance(expected_revision, bool)
                        or not isinstance(expected_revision, int)
                        or expected_revision != existing_package.document.revision
                    ):
                        raise ArchiveCollisionError(
                            "Target dance revision is stale; replacement was not applied"
                        )
                    next_revision = existing_package.document.revision + 1
                    if replacement_revision is not None:
                        if (
                            isinstance(replacement_revision, bool)
                            or not isinstance(replacement_revision, int)
                            or replacement_revision <= existing_package.document.revision
                        ):
                            raise ArchiveCollisionError(
                                "replacement_revision must be greater than the current revision"
                            )
                        next_revision = replacement_revision
                    package = replace(
                        package,
                        document=replace(
                            package.document,
                            revision=next_revision,
                        ),
                    )
        else:
            if copy_name is not None and (
                not isinstance(copy_name, str) or not copy_name.strip()
            ):
                raise ArchiveError("copy_name must be a non-empty dance name")
            if existing is not None and copy_name is None:
                raise ArchiveCollisionError(
                    f"Dance {package.dance_name!r} already exists; copy requires copy_name"
                )
            if copy_name is not None:
                name_collision = self._find_by_name(copy_name)
                if name_collision is not None:
                    raise ArchiveCollisionError(
                        f"Dance name {copy_name!r} already exists"
                    )
                if copy_name != package.dance_name:
                    package = _rename_package(package, copy_name)
        target = existing if replacing else self.dances_directory / uuid4().hex

        staged = self.dances_directory / f".staging-{uuid4().hex}"
        stage_ready = False
        try:
            try:
                self.dances_directory.mkdir(parents=True, exist_ok=True)
                staged.mkdir()
                self._write_package_directory(staged, package)
                self._inject("after_stage")
                self._inject("before_swap")
                stage_ready = True
            except OSError as error:
                raise ArchiveTransactionError(
                    f"Could not stage imported dance: {error}"
                ) from error
        finally:
            if not stage_ready and staged.exists():
                shutil.rmtree(staged, ignore_errors=True)

        backup_path: Path | None = None
        backup_moved = False
        promoted = False
        committed = False
        try:
            try:
                if replacing:
                    assert existing is not None
                    backup_path = self._backup_location()
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(existing, backup_path)
                    backup_moved = True
                    self._inject("after_backup")
                os.replace(staged, target)
                promoted = True
                self._inject("after_swap")
                committed = True
            except OSError as error:
                raise ArchiveTransactionError(
                    f"Could not promote imported dance: {error}"
                ) from error
        finally:
            if not committed:
                try:
                    if promoted and target.exists():
                        shutil.rmtree(target)
                    if backup_moved and backup_path is not None and backup_path.exists():
                        os.replace(backup_path, target)
                    if staged.exists():
                        shutil.rmtree(staged)
                except OSError as rollback_error:
                    raise ArchiveTransactionError(
                        f"Import rollback failed: {rollback_error}"
                    ) from rollback_error

        assert target is not None
        return self._result(target, package)

    def get(self, dance_id: str) -> ImportedDance:
        _validate_store_id(dance_id)
        path = self.dances_directory / dance_id
        with _exclusive_store_lock(self.root):
            if not path.is_dir():
                raise ArchiveNotFoundError(f"stored dance {dance_id!r} was not found")
            try:
                package = _validate_package_directory(path)
            except OSError as error:
                raise ArchiveError(
                    f"stored dance {dance_id!r} could not be read: {error}"
                ) from error
            return self._result(path, package)

    def find_by_name(self, dance_name: str) -> ImportedDance | None:
        if not isinstance(dance_name, str) or not dance_name.strip():
            raise ArchiveError("dance_name must be a non-empty string")
        with _exclusive_store_lock(self.root):
            path = self._find_by_name(dance_name)
            if path is None:
                return None
            try:
                package = _validate_package_directory(path)
            except OSError as error:
                raise ArchiveError(
                    f"stored dance {path.name!r} could not be read: {error}"
                ) from error
            return self._result(path, package)

    def list_dances(self) -> tuple[ImportedDance, ...]:
        with _exclusive_store_lock(self.root):
            if not self.dances_directory.is_dir():
                return ()
            dances = []
            for path in sorted(self.dances_directory.iterdir()):
                if (
                    not path.is_dir()
                    or path.name.startswith(".staging-")
                    or re.fullmatch(r"[a-f0-9]{32}", path.name) is None
                ):
                    continue
                try:
                    package = _validate_package_directory(path)
                except (ArchiveError, OSError):
                    continue
                dances.append(self._result(path, package))
            return tuple(dances)

    @contextmanager
    def locked_snapshot(
        self, dance_id: str
    ) -> Iterator[tuple[ImportedDance, Mapping[str, bytes]]]:
        _validate_store_id(dance_id)
        path = self.dances_directory / dance_id
        with _exclusive_store_lock(self.root):
            if not path.is_dir():
                raise ArchiveNotFoundError(f"stored dance {dance_id!r} was not found")
            try:
                package = _validate_package_directory(path)
            except OSError as error:
                raise ArchiveError(
                    f"stored dance {dance_id!r} could not be read: {error}"
                ) from error
            yield self._result(path, package), dict(package.assets)

    def _find_by_name(self, dance_name: str) -> Path | None:
        if not self.dances_directory.is_dir():
            return None
        for path in sorted(self.dances_directory.iterdir()):
            if (
                not path.is_dir()
                or path.name.startswith(".staging-")
                or re.fullmatch(r"[a-f0-9]{32}", path.name) is None
            ):
                continue
            try:
                package = _validate_package_directory(path)
            except OSError as error:
                raise ArchiveError(
                    f"stored dance {path.name!r} could not be read: {error}"
                ) from error
            if package.dance_name.casefold() == dance_name.casefold():
                return path
        return None

    def _write_package_directory(self, destination: Path, package: ArchivePackage) -> None:
        (destination / "figures").mkdir()
        for reference, content in sorted(package.figure_bytes.items()):
            (destination / "figures" / f"{reference}.json").write_bytes(content)
        if package.assets:
            for member, content in sorted(package.assets.items()):
                path = destination.joinpath(*PurePosixPath(member).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        (destination / "dance.json").write_bytes(_json_bytes(package.document.to_json()))
        (destination / "package.json").write_bytes(_json_bytes(dict(package.manifest)))

    def _backup_location(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        return self.backups_directory / f"{timestamp}-{uuid4().hex}"

    def _inject(self, point: str) -> None:
        if self.failure_injector is not None:
            self.failure_injector(point)

    def _result(self, path: Path, package: ArchivePackage) -> ImportedDance:
        repository = FigureRepository(
            path / "figures",
            path / "_no_shared_figure_fallback",
        )
        return ImportedDance(
            dance_id=path.name,
            document=package.document,
            path=path,
            repository=repository,
            package_id=package.package_id,
        )


def _validate_content(
    manifest: dict[str, Any],
    dance_json: dict[str, Any],
    figure_bytes: Mapping[str, bytes],
    assets: Mapping[str, bytes],
) -> ArchivePackage:
    members = {"package.json": _json_bytes(manifest), "dance.json": _json_bytes(dance_json)}
    members.update(
        {f"figures/{reference}.json": content for reference, content in figure_bytes.items()}
    )
    members.update(assets)
    return _validate_members_in_memory(members)


def _validate_members_in_memory(members: Mapping[str, bytes]) -> ArchivePackage:
    return _validate_package_members(members)


def _validate_written_archive(path: Path) -> None:
    size = path.stat().st_size
    if size > _MAX_ARCHIVE_BYTES:
        raise ArchiveError(
            f"package: compressed archive size exceeds {_MAX_ARCHIVE_BYTES} bytes"
        )
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        _validate_archive_names([info.filename for info in infos])
        _validate_archive_info_limits(infos)


def _validate_package_directory(path: Path) -> ArchivePackage:
    if path.is_symlink() or not path.is_dir():
        raise ArchiveError(f"stored dance directory {path} is missing or unsafe")
    members: dict[str, bytes] = {}
    total_size = 0
    for file_path in path.rglob("*"):
        if file_path.is_symlink():
            raise ArchiveError(f"{file_path}: stored package may not contain symbolic links")
        if file_path.is_dir():
            continue
        if not file_path.is_file():
            raise ArchiveError(f"{file_path}: unexpected non-file package entry")
        member_name = file_path.relative_to(path).as_posix()
        _validate_member_path(member_name)
        if len(members) >= _MAX_MEMBER_COUNT:
            raise ArchiveError(f"package: member count exceeds {_MAX_MEMBER_COUNT}")
        remaining_total = _MAX_TOTAL_UNCOMPRESSED_BYTES - total_size
        read_limit = min(_MAX_MEMBER_BYTES, remaining_total)
        with file_path.open("rb") as member:
            content = member.read(read_limit + 1)
        if len(content) > read_limit:
            raise ArchiveError(f"{member_name}: stored package exceeds size limits")
        members[member_name] = content
        total_size += len(content)
    return _validate_members_in_memory(members)


def _rename_package(package: ArchivePackage, dance_name: str) -> ArchivePackage:
    dance_json = package.document.to_json()
    dance_json["metadata"]["name"] = dance_name
    document = DanceDocument.from_json(dance_json)
    manifest = dict(package.manifest)
    manifest["danceName"] = dance_name
    return ArchivePackage(
        package_id=package.package_id,
        dance_name=dance_name,
        document=document,
        figures=package.figures,
        assets=package.assets,
        incomplete=package.incomplete,
        manifest=manifest,
        figure_bytes=package.figure_bytes,
    )


def _validate_package_semantics(
    document: DanceDocument,
    figures: Mapping[str, dict[str, Any]],
) -> None:
    unresolved = set(document.unresolved_references)
    refs_in_tree = _document_references(document)
    if not unresolved.issubset(refs_in_tree):
        raise ArchiveError("dance.json.unresolvedReferences: unresolved ref is absent from tree")
    if document.incomplete != bool(unresolved):
        raise ArchiveError("dance.json.status: incomplete status and unresolved refs disagree")

    for ref, definition in figures.items():
        location = f"figures/{ref}.json"
        _validate_figure_ref(ref, location)
        if definition.get("Name") != ref:
            raise ArchiveError(
                f"{location}.Name: definition name does not match declared figure reference {ref!r}"
            )
        version = definition.get("Version")
        if isinstance(version, bool) or not isinstance(version, int) or version not in (2, 3):
            raise ArchiveError(f"{location}.Version: only figure versions 2 and 3 are supported")
        if version == 2:
            _validate_atomic_definition(ref, definition, location)
        else:
            if "FigureList" not in definition:
                raise ArchiveError(f"{location}.FigureList: composite definition is missing FigureList")
            try:
                parsed = LegacyDanceAdapter.from_data(
                    definition,
                    lambda figure_ref: figure_ref in figures,
                    get_definition=lambda figure_ref: figures.get(figure_ref),
                )
            except (TypeError, ValueError) as error:
                raise ArchiveError(f"{location}.FigureList: invalid composite tree: {error}") from error
            if parsed.unresolved_references:
                not_declared = set(parsed.unresolved_references) - unresolved
                if not_declared:
                    missing = sorted(not_declared)[0]
                    raise ArchiveError(
                        f"{location}.FigureList: referenced definition {missing!r} is missing "
                        "and is not declared unresolved"
                    )
            _validate_document_addons(parsed, figures, location)

    expected = refs_in_tree - unresolved
    expanded = set(expected)
    pending = list(sorted(expected))
    while pending:
        reference = pending.pop()
        definition = figures.get(reference)
        if definition is None:
            raise ArchiveError(
                f"dance.json: reference {reference!r} has no matching packaged definition"
            )
        if definition.get("Version") != 3:
            continue
        try:
            composite = LegacyDanceAdapter.from_data(
                definition,
                lambda ref: ref in figures,
                get_definition=lambda ref: figures.get(ref),
            )
        except (TypeError, ValueError) as error:
            raise ArchiveError(
                f"figures/{reference}.json.FigureList: invalid composite tree: {error}"
            ) from error
        found = _document_references(composite)
        missing = found - set(figures) - unresolved
        if missing:
            child = sorted(missing)[0]
            raise ArchiveError(
                f"figures/{reference}.json.FigureList: referenced definition {child!r} is missing"
            )
        additions = found - expanded - unresolved
        expanded.update(additions)
        pending.extend(sorted(additions))

    extra = set(figures) - expanded
    if extra:
        raise ArchiveError(
            f"figures/{sorted(extra)[0]}.json: definition is not referenced by dance.json "
            "or another bundled composite"
        )
    _validate_document_addons(document, figures, "dance.json")


def _validate_document_addons(
    document: DanceDocument,
    figures: Mapping[str, dict[str, Any]],
    context: str,
) -> None:
    for path, node in _walk_with_paths(document.root):
        if not isinstance(node, (FigureOccurrence, CompositeOccurrence)):
            continue
        _validate_figure_ref(node.figure_ref, f"{context} {path}.figureRef")
        try:
            finite_anchor = all(isfinite(value) for value in node.anchor)
        except OverflowError:
            finite_anchor = False
        if not finite_anchor:
            raise ArchiveError(
                f"{context} {path}.anchor: coordinates must be finite real numbers"
            )
        definition = figures.get(node.figure_ref)
        if definition is None:
            if node.figure_ref in document.unresolved_references:
                continue
            raise ArchiveError(
                f"{context} {path}.figureRef: definition {node.figure_ref!r} is missing"
            )
        location = f"{context} {path}"
        if definition.get("Version") == 3:
            if node.addons:
                raise ArchiveError(
                    f"{location}.addons: composite figure {node.figure_ref!r} does not support addons"
                )
            if not isinstance(node, CompositeOccurrence):
                raise ArchiveError(
                    f"{location}.figureRef: composite definition requires a compositeOccurrence"
                )
            continue
        if isinstance(node, CompositeOccurrence):
            raise ArchiveError(
                f"{location}.figureRef: compositeOccurrence must reference a Version 3 definition"
            )
        _validate_selected_addons(node, definition, location)


def _validate_atomic_definition(
    reference: str,
    definition: dict[str, Any],
    location: str,
) -> None:
    if not isinstance(definition.get("Name"), str) or not definition["Name"]:
        raise ArchiveError(f"{location}.Name: expected a non-empty string")
    if not isinstance(definition.get("Desc", ""), str):
        raise ArchiveError(f"{location}.Desc: expected a string")
    bars = definition.get("Bars")
    if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
        raise ArchiveError(f"{location}.Bars: expected a positive integer")
    formation = definition.get("Formation")
    if formation is not None and not isinstance(formation, str):
        raise ArchiveError(f"{location}.Formation: expected a string or null")
    capability_version = definition.get("CapabilityVersion", 1)
    if isinstance(capability_version, bool) or not isinstance(capability_version, int) or capability_version < 1:
        raise ArchiveError(f"{location}.CapabilityVersion: expected a positive integer")
    try:
        valid_addons = FigureRepository._normalize_addons(definition.get("Addons", {}))
        FigureRepository._parse_combination_validator(
            definition.get("AddonCombinationValidator"),
            {addon["name"] for addon in valid_addons},
        )
    except (TypeError, ValueError) as error:
        raise ArchiveError(f"{location}.Addons: invalid capability definition: {error}") from error


def _validate_selected_addons(
    node: FigureOccurrence,
    definition: dict[str, Any],
    location: str,
) -> None:
    try:
        valid = FigureRepository._normalize_addons(definition.get("Addons", {}))
        combinations = FigureRepository._parse_combination_validator(
            definition.get("AddonCombinationValidator"),
            {addon["name"] for addon in valid},
        )
    except (TypeError, ValueError) as error:
        raise ArchiveError(
            f"figures/{node.figure_ref}.json.Addons: invalid capability definition: {error}"
        ) from error
    valid_names = {addon["name"] for addon in valid}
    duration_names = [name for name in node.addons if duration_addon_bars(name) is not None]
    if len(duration_names) > 1:
        raise ArchiveError(
            f"{location}.addons: conflicting duration addons {duration_names[0]!r} and "
            f"{duration_names[1]!r} both modify Bars"
        )
    for index, addon in enumerate(node.addons):
        if addon not in valid_names and duration_addon_bars(addon) is None:
            raise ArchiveError(
                f"{location}.addons[{index}]: addon {addon!r} is not supported by "
                f"{node.figure_ref!r}"
            )
        if addon in node.addons[:index]:
            raise ArchiveError(
                f"{location}.addons[{index}]: duplicate addon {addon!r}"
            )
    try:
        FigureRepository._validate_selected_conflicts(
            node.addons, valid, node.figure_ref, location, node.id
        )
    except ValueError as error:
        raise ArchiveError(f"{location}.addons: {error}") from error
    combination_selection = frozenset(
        addon for addon in node.addons if duration_addon_bars(addon) is None
    )
    if combinations is not None and combination_selection not in combinations:
        raise ArchiveError(f"{location}.addons: addon combination is not supported")


def _walk_with_paths(root: DanceNode):
    def walk(node: DanceNode, path: str):
        yield path, node
        if isinstance(node, CompositeOccurrence):
            yield from walk(node.root, f"{path}.root")
        elif hasattr(node, "children"):
            for index, child in enumerate(node.children):
                yield from walk(child, f"{path}.children[{index}]")

    yield from walk(root, "root")


def _document_references(document: DanceDocument) -> set[str]:
    return {
        node.figure_ref
        for node in DanceDocument._walk(document.root)
        if isinstance(node, (FigureOccurrence, CompositeOccurrence))
    }


def _dance_name(document: DanceDocument) -> str:
    name = document.metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ArchiveError("dance.json.metadata.name: expected a non-empty dance name")
    return name


def _validate_archive_names(names: list[str]) -> None:
    seen: set[str] = set()
    folded: set[str] = set()
    for name in names:
        if name in seen or name.casefold() in folded:
            raise ArchiveError(f"{name}: duplicate archive member name")
        seen.add(name)
        folded.add(name.casefold())
        _validate_member_path(name)
    for name in names:
        components = name.split("/")
        for index in range(1, len(components)):
            parent = "/".join(components[:index])
            if parent.casefold() in folded:
                raise ArchiveError(f"{name}: path conflict with member {parent}")


def _validate_member_path(member: str, required_prefix: str | None = None) -> None:
    if not isinstance(member, str) or not member or "\\" in member or "\x00" in member:
        raise ArchiveError(f"{member!r}: unsafe archive member path")
    path = PurePosixPath(member)
    components = member.split("/")
    if (
        path.is_absolute()
        or any(part in ("", ".", "..") for part in components)
        or any(not _windows_safe_component(part) for part in components)
        or member.endswith("/")
    ):
        raise ArchiveError(f"{member!r}: unsafe archive member path")
    if required_prefix is not None and not member.startswith(required_prefix):
        raise ArchiveError(f"{member!r}: asset members must be under {required_prefix}")
    if required_prefix is None and not (
        member in ("package.json", "dance.json")
        or member.startswith("figures/")
        or member.startswith("assets/")
    ):
        raise ArchiveError(f"{member!r}: unexpected archive member path")


def _validate_figure_ref(reference: Any, context: str) -> None:
    if (
        not isinstance(reference, str)
        or not reference
        or reference.strip() != reference
        or reference in (".", "..")
        or "/" in reference
        or "\\" in reference
        or "\x00" in reference
        or not _windows_safe_component(reference)
    ):
        raise ArchiveError(f"{context}: invalid figure reference {reference!r}")


def _validate_store_id(dance_id: str) -> None:
    if not isinstance(dance_id, str) or re.fullmatch(r"[a-f0-9]{32}", dance_id) is None:
        raise ArchiveError(f"invalid stored dance id {dance_id!r}")


def _windows_safe_component(component: str) -> bool:
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
    return (
        bool(component)
        and not any(char in component for char in '<>:"|?*')
        and not any(ord(char) < 32 for char in component)
        and not component.endswith((".", " "))
        and component.split(".", 1)[0].upper() not in reserved
    )


def _decode_json(content: bytes, location: str) -> Any:
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"invalid JSON constant {value}")

    def parse_finite_float(value):
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError(f"non-finite JSON number {value}")
        return parsed

    try:
        return json.loads(
            content.decode("utf-8-sig"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
            parse_float=parse_finite_float,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ) as error:
        raise ArchiveError(f"{location}: invalid JSON: {error}") from error


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ArchiveError(f"content is not valid JSON: {error}") from error


def _write_zip_member(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, content)
