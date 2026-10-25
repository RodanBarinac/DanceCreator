from __future__ import annotations

import base64
import io
import json
from math import isfinite
import os
import re
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Blueprint, jsonify, request

from src.engine.domain.dance_model import (
    CompositeOccurrence,
    DanceDocument,
    DanceNode,
    FigureOccurrence,
    GroupNode,
)
from src.engine.domain.legacy_adapter import LegacyDanceAdapter
from src.engine.editing.commands import (
    CreateGroup,
    DeleteNode,
    InsertOccurrence,
    MoveNode,
    ReorderNode,
    UpdateAddons,
    UpdateAnchor,
    UpdateOccurrence,
)
from src.engine.editing.history import History
from src.engine.editing.proposals import Proposal, create_proposal
from src.engine.editing.state import (
    EditorState,
    StateInitializationError,
    apply_proposal,
    create_state,
)
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.execution.executor import ExecutionResult, execute_document
from src.engine.execution.duration import ExecutionError
from src.engine.figures.capabilities import AddonValidationError, FigureRepository
from src.engine.models.DanceFloor import DanceFloor, default_facing_target
from src.engine.persistence.FileManager import FileManager
from src.engine.persistence.archive import (
    ArchiveCollisionError,
    ArchiveError,
    ArchiveNotFoundError,
    ArchiveStore,
    export_archive_bytes,
    validate_archive,
)
from src.engine.validation import validate_document


def create_canonical_blueprint(app_module: Any) -> Blueprint:
    bp = Blueprint("canonical_api", __name__)
    documents: dict[str, DanceDocument] = {}
    histories: dict[str, History] = {}
    persisted_revisions: dict[str, int] = {}
    dance_locks: dict[str, threading.RLock] = {}
    lock_guard = threading.Lock()
    proposals: dict[str, tuple[str, int, Proposal]] = {}

    def dance_lock(key: str):
        with lock_guard:
            return dance_locks.setdefault(key, threading.RLock())

    def archive_store() -> ArchiveStore:
        return ArchiveStore(Path(app_module.DANCES_DIR) / ".archive-store")

    def repository() -> FigureRepository:
        return FigureRepository(app_module.FIGURES_DIR, app_module.DANCES_DIR)

    def resolve(identifier: str) -> Path | None:
        if re.fullmatch(r"[a-f0-9]{32}", identifier):
            return archive_store().dances_directory / identifier
        root = Path(app_module.DANCES_DIR).resolve()
        raw = identifier[:-5] if identifier.lower().endswith(".json") else identifier
        if not raw or Path(raw).name != raw:
            return None
        candidates = [root / f"{raw}.json", root / identifier]
        for candidate in candidates:
            if candidate.is_file() and candidate.resolve().parent == root:
                return candidate
        return None

    def cache_key(path: Path) -> str:
        return str(path.resolve())

    def is_archive_path(path: Path) -> bool:
        return (
            path.parent.resolve() == archive_store().dances_directory.resolve()
            and re.fullmatch(r"[a-f0-9]{32}", path.name) is not None
        )

    def invalidate_dance(key: str) -> None:
        documents.pop(key, None)
        histories.pop(key, None)
        persisted_revisions.pop(key, None)
        for token, proposal_record in list(proposals.items()):
            if proposal_record[0] == key:
                proposals.pop(token, None)

    def load(path: Path) -> tuple[str, DanceDocument, History]:
        key = cache_key(path)
        with dance_lock(key):
            stored = None
            revision_floor = None
            if key in histories and is_archive_path(path):
                stored = archive_store().get(path.name)
                if persisted_revisions.get(key) == stored.document.revision:
                    history = histories[key]
                    return key, history.state.document, history
                revision_floor = histories[key].state.document.revision
                invalidate_dance(key)
            elif key in histories:
                history = histories[key]
                return key, history.state.document, history
            return _load(path, key, stored, revision_floor)

    def _load(
        path: Path,
        key: str,
        stored: Any = None,
        revision_floor: int | None = None,
    ) -> tuple[str, DanceDocument, History]:
        if is_archive_path(path):
            imported = stored or archive_store().get(path.name)
            repo = imported.repository
            document = imported.document
            persisted_revisions[key] = document.revision
            if revision_floor is not None and document.revision <= revision_floor:
                document = replace(document, revision=revision_floor + 1)
        else:
            repo = repository()
            with path.open("r", encoding="utf-8-sig") as source:
                data = json.load(source)
            if isinstance(data, dict) and data.get("formatVersion") == 1:
                document = DanceDocument.from_json(data)
            else:
                document = LegacyDanceAdapter.from_data(
                    data,
                    repo.figure_exists,
                    get_definition=repo.get_legacy_definition,
                )
        shape = document.metadata.get("shape", document.metadata.get("Shape", ""))
        shape_count = str(shape).split("/", 1)[0]
        configured_count = app_module.app.config.get("DEFAULT_COUPLES", 1)
        couples = (
            int(shape_count)
            if shape_count.isdigit() and int(shape_count) > 0
            else configured_count
        )
        floor = FloorState.from_legacy(DanceFloor("api-initial", couples))
        if document.incomplete:
            state = EditorState(
                document,
                ExecutionResult(None, None, (), (), status="failed", last_valid_floor=floor),
                floor,
                repo,
            )
        else:
            try:
                state = create_state(document, floor, repo)
            except StateInitializationError as initialization_error:
                try:
                    execution = execute_document(document, floor, repo)
                except (ExecutionError, OSError, TypeError, ValueError, KeyError):
                    execution = ExecutionResult(
                        None,
                        None,
                        (),
                        initialization_error.report.errors,
                        status="failed",
                        last_valid_floor=floor,
                    )
                state = EditorState(document, execution, floor, repo)
        history = History(state)
        documents[key] = document
        histories[key] = history
        return key, document, history

    def error(
        code: str, message: str, status: int, *, dancers: list[str] | tuple[str, ...] | None = None, **details: Any
    ):
        payload = {"error": {"code": code, "message": message}}
        if dancers is not None:
            payload["error"]["dancers"] = list(dancers)
        if details:
            payload["error"]["details"] = details
        return jsonify(payload), status

    def serialize_floor(floor: Any) -> dict[str, Any] | None:
        if floor is None:
            return None
        return {
            app_module._dance_position_key(position): {
                "position": [position[0], position[1]],
                "dancer": {
                    "name": entry.dancer_name,
                    "gender": entry.dancer_gender,
                },
                "facing": entry.facing,
            }
            for position, entry in sorted(floor.positions.items())
        }

    def serialize_trace(records: Any) -> list[dict[str, Any]]:
        return [
            {
                "nodeId": record.node_id,
                "kind": record.kind,
                "path": list(record.node_path),
                "groupPath": list(record.group_path),
                "parentGroup": record.parent_group,
                "figureRef": record.figure_ref,
                "barRange": list(record.bar_range) if record.bar_range else None,
                "status": record.status,
                "incomingFloor": serialize_floor(record.incoming_floor),
                "outgoingFloor": serialize_floor(record.outgoing_floor),
                "writes": [list(position) for position in sorted(record.writes)],
                "branches": [
                    {
                        "nodeId": branch.node_id,
                        "status": branch.status,
                        "outgoingFloor": serialize_floor(branch.outgoing_floor),
                        "writes": [list(position) for position in sorted(branch.writes)],
                    }
                    for branch in record.branch_summaries
                ],
                "conflict": (
                    {
                        "code": record.conflict.code,
                        "groupId": record.conflict.group_id,
                        "positions": [
                            {"position": list(position), "branches": list(branches)}
                            for position, branches in record.conflict.conflicts.items()
                        ],
                    }
                    if record.conflict
                    else None
                ),
            }
            for record in records
        ]

    def project(node: DanceNode, path: str = "root") -> dict[str, Any]:
        result = {
            "id": node.id,
            "path": path,
            "type": (
                "group" if isinstance(node, GroupNode)
                else "compositeOccurrence" if isinstance(node, CompositeOccurrence)
                else "figure"
            ),
        }
        if isinstance(node, GroupNode):
            result.update(
                kind=node.kind,
                children=[
                    project(child, f"{path}.children[{index}]")
                    for index, child in enumerate(node.children)
                ],
            )
        elif isinstance(node, CompositeOccurrence):
            result.update(
                figureRef=node.figure_ref,
                anchor=list(node.anchor),
                addons=list(node.addons),
                root=project(node.root, f"{path}.root"),
            )
        else:
            result.update(
                figureRef=node.figure_ref,
                anchor=list(node.anchor),
                addons=list(node.addons),
            )
        return result

    def structured_crips(document: DanceDocument, state: Any) -> list[dict[str, Any]]:
        from src.engine.models.Dance import getCripsData

        effective_anchors: dict[str, tuple[Any, Any]] = {}

        def visit(node: DanceNode, offset=(0, 0)) -> None:
            if isinstance(node, CompositeOccurrence):
                nested_offset = (
                    offset[0] + node.anchor[0],
                    offset[1] + node.anchor[1],
                )
                visit(node.root, nested_offset)
            elif isinstance(node, GroupNode):
                for child in node.children:
                    visit(child, offset)
            else:
                effective_anchors[node.id] = (
                    node.anchor[0] + offset[0],
                    node.anchor[1] + offset[1],
                )

        visit(document.root)
        lines = []
        for record in state.trace:
            if record.kind != "figure" or record.figure_ref is None:
                continue
            occurrence = document.find_node(record.node_id)
            anchor = effective_anchors.get(record.node_id, occurrence.anchor)
            figure_node = replace(occurrence, anchor=anchor)
            bar_start = record.bar_range[0] if record.bar_range else 1
            legacy_floor = record.incoming_floor.to_legacy()
            max_row = max(
                (position[0] for position in legacy_floor.DanceFloorMap),
                default=0,
            )
            legacy_floor.setupDanceFloorNames(int(max_row))
            figure_lines = getCripsData(
                figure_node, legacy_floor, bar_start=bar_start
            )
            if record.bar_range is not None:
                for line in figure_lines:
                    line["barRange"] = list(record.bar_range)
            lines.extend(figure_lines)
        return lines

    def document_response(document: DanceDocument, history: History, *, status: int = 200):
        state = history.state
        validation = validate_document(
            document, state.initial_floor, state.repository
        ).to_dict()
        body = {
            "document": document.to_json(),
            "tree": project(document.root),
            "trace": serialize_trace(state.trace),
            "crips": structured_crips(document, state),
            "execution": {
                "status": state.execution_result.status,
                "executable": state.execution_result.status == "completed",
                "lastValidFloor": serialize_floor(
                    state.execution_result.last_valid_floor
                ),
            },
            "validation": validation,
            "revision": document.revision,
            "etag": f'"{document.revision}"',
        }
        response = jsonify(body)
        response.headers["ETag"] = body["etag"]
        return response, status

    def expected_revision(body: Any) -> int | None:
        supplied = []
        if isinstance(body, dict):
            for name in ("baseRevision", "expectedRevision"):
                if name in body:
                    supplied.append(body[name])
        header = request.headers.get("If-Match")
        if header is not None:
            value = header.strip()
            if value.startswith("W/"):
                value = value[2:]
            if len(value) < 2 or value[0] != '"' or value[-1] != '"':
                raise ValueError("If-Match must contain a quoted revision.")
            try:
                supplied.append(int(value[1:-1]))
            except ValueError as exc:
                raise ValueError("If-Match must contain a quoted integer revision.") from exc
        if not supplied:
            return None
        first = supplied[0]
        if isinstance(first, bool) or not isinstance(first, int) or first < 0:
            raise ValueError("Expected revision must be a non-negative integer.")
        if any(value != first for value in supplied[1:]):
            raise ValueError("Request revision and If-Match do not agree.")
        return first

    def check_revision(expected: int | None, current: int):
        if expected is None:
            return error(
                "malformed_request",
                "An expected revision or If-Match header is required.",
                400,
            )
        if expected != current:
            return error(
                "revision_conflict",
                "Document revision is stale.",
                409,
                expectedRevision=expected,
                actualRevision=current,
            )
        return None

    def command_from_json(data: Any):
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            raise ValueError("command must be an object with a type")
        kind = data["type"]
        if kind == "updateAnchor":
            return UpdateAnchor(data["nodeId"], tuple(data["anchor"]))
        if kind == "updateAddons":
            return UpdateAddons(data["nodeId"], tuple(data["addons"]))
        if kind == "updateOccurrence":
            return UpdateOccurrence(
                data["nodeId"], tuple(data["anchor"]), tuple(data["addons"])
            )
        if kind == "deleteNode":
            return DeleteNode(data["nodeId"])
        if kind == "reorderNode":
            return ReorderNode(data["nodeId"], data["index"])
        if kind == "moveNode":
            return MoveNode(data["nodeId"], data["destinationGroupId"], data["index"])
        if kind == "createGroup":
            return CreateGroup(data["parentGroupId"], data["kind"], data["index"])
        if kind == "insertOccurrence":
            return InsertOccurrence(
                data["parentGroupId"], data["figureRef"], data["index"],
                tuple(data.get("anchor", (0, 0))), tuple(data.get("addons", ())),
            )
        raise ValueError(f"unsupported command type: {kind}")

    def persist(path: Path, document: DanceDocument) -> None:
        if is_archive_path(path):
            stored = archive_store().get(path.name)
            asset_directory = path / "assets"
            assets = (
                {
                    file_path.relative_to(path).as_posix(): file_path.read_bytes()
                    for file_path in asset_directory.rglob("*")
                    if file_path.is_file()
                }
                if asset_directory.is_dir()
                else {}
            )
            package_bytes = export_archive_bytes(
                document,
                stored.repository,
                assets=assets,
                package_id=stored.package_id,
            )
            archive_store().import_archive(
                package_bytes,
                collision="replace",
                confirm_replace=True,
                expected_revision=stored.document.revision,
                replacement_revision=document.revision,
                target_id=stored.dance_id,
            )
            return
        FileManager.write_json_safe(str(path), document.to_json(), create_backup=path.exists())

    @bp.get("/api/figures")
    def figures():
        repo = repository()
        result = []
        root = Path(app_module.FIGURES_DIR)
        if root.is_dir():
            for path in sorted(root.glob("*.json")):
                try:
                    raw_definition = repo.get_legacy_definition(path.stem)
                    if raw_definition["Version"] == 3:
                        result.append({
                            "figureRef": path.stem,
                            "name": raw_definition.get("Name", path.stem),
                            "description": raw_definition.get("Desc", ""),
                            "version": 3,
                            "capabilities": None,
                        })
                        continue
                    definition = repo.get_definition(path.stem)
                    capabilities = repo.get_capabilities(path.stem)
                except (OSError, ValueError, FileNotFoundError):
                    continue
                result.append({
                    "figureRef": definition.figure_ref,
                    "name": definition.name,
                    "description": definition.description,
                    "version": definition.version,
                    "capabilities": {
                        "bars": capabilities.bars,
                        "formation": capabilities.formation,
                        "validAddons": list(capabilities.valid_addons),
                        "supportsPreview": capabilities.supports_preview,
                        "capabilityVersion": capabilities.capability_version,
                        "durationAddonPattern": capabilities.duration_addon_pattern,
                    },
                })
        return jsonify({"figures": result})

    @bp.post("/api/figures/<path:identifier>/preview")
    def figure_preview(identifier: str):
        repo = repository()
        preview_dancers: list[str] = []
        try:
            definition = repo.get_legacy_definition(identifier)
            if definition["Version"] != 2:
                return error(
                    "preview_unsupported",
                    "Isolated preview is available for simple figures only.",
                    422,
                )
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return error("invalid_preview", "Preview request must be a JSON object.", 400)
            anchor = payload.get("anchor", [1, 0])
            addons = payload.get("addons", [])
            if (
                not isinstance(anchor, list)
                or len(anchor) != 2
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                    for value in anchor
                )
            ):
                return error(
                    "invalid_preview",
                    "Preview anchor must contain two numbers.",
                    400,
                )
            if not isinstance(addons, list) or any(
                not isinstance(addon, str) for addon in addons
            ):
                return error(
                    "invalid_preview",
                    "Preview addons must be an array of names.",
                    400,
                )
            repo.validate_addons(identifier, addons, path="preview")
            from src.engine.figures.SimpleFigure import SimpleFigure

            figure = SimpleFigure(identifier, list(anchor), addons)
            preview_dancers = [f"start position {index + 1}" for index in range(len(figure.StartPos))]
            start_positions = list(figure.StartPos)
            end_positions = list(figure.EndPos)
            start_facings = list(figure.StartFacing)
            facings = list(figure.EndFacing)
            start_dancers = list(figure.StartDancers)
            if not start_positions or len(start_positions) != len(end_positions):
                return error(
                    "preview_unsupported",
                    "Figure must define matching active start and end dancers.",
                    422, dancers=preview_dancers,
                )
            def valid_positions(positions):
                return all(
                    isinstance(position, (list, tuple))
                    and len(position) == 2
                    and all(
                        not isinstance(value, bool)
                        and isinstance(value, (int, float))
                        and isfinite(value)
                        for value in position
                    )
                    for position in positions
                )

            if not valid_positions(start_positions) or not valid_positions(end_positions):
                return error(
                    "preview_unsupported",
                    "Figure start and end positions must be finite coordinate pairs.",
                    422, dancers=preview_dancers,
                )
            couples = max((int(dancer[:-1]) for dancer in start_dancers), default=0)
            anchored_starts = [
                tuple(figure.posWithAnchor(position)) for position in start_positions
            ]
            anchored_ends = [
                tuple(figure.posWithAnchor(position)) for position in end_positions
            ]
            if len(set(anchored_starts)) != len(anchored_starts):
                return error(
                    "invalid_preview",
                    "Figure start positions overlap for this preview.",
                    422, dancers=preview_dancers,
                )
            if len(set(anchored_ends)) != len(anchored_ends):
                return error(
                    "invalid_preview",
                    "Figure end positions overlap for this preview.",
                    422, dancers=preview_dancers,
                )

            def facing_target(
                index: int,
                positions: list[tuple[Any, Any]],
                declarations: list[Any],
            ):
                facing = declarations[index] if index < len(declarations) else None
                if isinstance(facing, (list, tuple)) and len(facing) == 2:
                    return tuple(figure.posWithAnchor(facing))
                return tuple(default_facing_target(positions[index]))

            incoming_positions = {}
            for index, position in enumerate(anchored_starts):
                name = start_dancers[index]
                gender = "male" if name.endswith("m") else "female"
                incoming_positions[position] = FloorEntry(
                    name,
                    gender,
                    facing_target(index, anchored_starts, start_facings),
                )
            incoming = FloorState(incoming_positions)
            moved_floor = figure.DanceMove(incoming.to_legacy())
            moved_by_position = {
                tuple(position): dancer
                for position, (dancer, _) in moved_floor.DanceFloorMap.items()
            }
            if any(position not in moved_by_position for position in anchored_ends):
                return error(
                    "preview_failed",
                    "Figure execution did not produce all active dancers.",
                    422, dancers=preview_dancers,
                )
            outgoing_positions = {}
            for index, position in enumerate(anchored_ends):
                dancer = moved_by_position[position]
                outgoing_positions[position] = FloorEntry(
                    str(dancer.name),
                    str(getattr(dancer, "gender", "")),
                    facing_target(index, anchored_ends, facings),
                )
            outgoing = FloorState(outgoing_positions)
            from src.engine.models.Dance import getCripsData

            crips_floor = incoming.to_legacy()
            rows = [position[0] for position in crips_floor.DanceFloorMap]
            rows.extend(
                figure.posWithAnchor(position)[0]
                for position in list(figure.EndPos) + [
                    facing for facing in figure.EndFacing
                    if isinstance(facing, (list, tuple)) and len(facing) == 2
                ]
            )
            crips_floor.setupDanceFloorNames(int(max(rows, default=0)))
            crips = getCripsData(figure, crips_floor, bar_start=1)
        except FileNotFoundError:
            return error("not_found", "Figure was not found.", 404)
        except AddonValidationError as exc:
            return error(
                exc.code,
                exc.message,
                400,
                figureRef=exc.figure_ref,
                addons=list(exc.addons),
                path=exc.path,
                occurrenceId=exc.occurrence_id,
                dancers=exc.dancers,
            )
        except (ValueError, OSError) as exc:
            return error("invalid_preview", str(exc), 400, dancers=preview_dancers)
        except Exception as exc:
            return error("preview_failed", str(exc), 422, dancers=preview_dancers)
        return jsonify({
            "figureRef": identifier,
            "couples": couples,
            "incomingFloor": serialize_floor(incoming),
            "outgoingFloor": serialize_floor(outgoing),
            "crips": crips,
        })

    @bp.post("/api/dances/<path:identifier>/nodes/<node_id>/preview")
    def dance_node_preview(identifier: str, node_id: str):
        try:
            path, document, history = get_dance(identifier)
        except ValueError as exc:
            return error("invalid_document", str(exc), 400)
        if path is None:
            return error("not_found", "Dance was not found.", 404)

        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error("invalid_preview", "Preview request must be a JSON object.", 400)
        if set(body) != {"anchor", "addons"}:
            return error("invalid_preview", "Preview request must contain only anchor and addons.", 400)
        anchor = body.get("anchor")
        addons = body.get("addons")
        if (
            not isinstance(anchor, list)
            or len(anchor) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                for value in anchor
            )
        ):
            return error("invalid_preview", "Preview anchor must contain two numbers.", 400)
        if not isinstance(addons, list) or any(not isinstance(addon, str) for addon in addons):
            return error("invalid_preview", "Preview addons must be an array of names.", 400)

        try:
            node = document.find_node(node_id)
        except KeyError:
            return error("node_not_found", "Dance node was not found.", 404)
        if not isinstance(node, FigureOccurrence):
            return error(
                "preview_unsupported",
                "Preview is available for simple figure nodes only.",
                422,
            )
        record = next(
            (
                item for item in history.state.trace
                if item.node_id == node_id and item.kind == "figure"
            ),
            None,
        )
        if record is None:
            try:
                start_count = len(repository().get_legacy_definition(node.figure_ref).get("StartPos", []))
            except (FileNotFoundError, OSError, ValueError, TypeError):
                start_count = 0
            return error(
                "preview_failed",
                "The dance trace has no incoming floor for this figure node.",
                422,
                dancers=[f"start position {index + 1}" for index in range(start_count)],
            )

        def parent_offset(current: DanceNode, target_id: str, offset=(0, 0)):
            if isinstance(current, CompositeOccurrence):
                if current.id == target_id:
                    return None
                nested = (offset[0] + current.anchor[0], offset[1] + current.anchor[1])
                return parent_offset(current.root, target_id, nested)
            if isinstance(current, GroupNode):
                for child in current.children:
                    found = parent_offset(child, target_id, offset)
                    if found is not None:
                        return found
                return None
            if isinstance(current, FigureOccurrence) and current.id == target_id:
                return offset
            return None

        offset = parent_offset(document.root, node_id)
        offset = offset or (0, 0)
        effective_anchor = (anchor[0] + offset[0], anchor[1] + offset[1])
        incoming = record.incoming_floor
        affected_dancers: list[str] = []
        try:
            repo = history.state.repository
            repo.validate_addons(node.figure_ref, addons, path=f"preview.{node_id}", occurrence_id=node_id)
            from src.engine.figures.SimpleFigure import SimpleFigure

            figure = SimpleFigure(node.figure_ref, list(effective_anchor), addons)
            for index, start in enumerate(figure.StartPos):
                position = tuple(figure.posWithAnchor(start))
                entry = incoming.positions.get(position)
                affected_dancers.append(
                    entry.dancer_name if entry is not None else f"start position {index + 1}"
                )
            candidate = replace(
                node,
                anchor=effective_anchor,
                addons=tuple(addons),
            )
            isolated_document = DanceDocument(
                document.format_version,
                {},
                GroupNode(f"preview-root-{uuid4().hex}", "series", (candidate,)),
            )
            execution = execute_document(isolated_document, incoming, repo)
            if execution.status != "completed" or execution.outgoing_floor is None:
                return error(
                    "preview_failed",
                    "The proposed figure did not produce a valid outgoing floor.",
                    422,
                    dancers=affected_dancers,
                )

            from src.engine.models.Dance import getCripsData

            legacy_floor = incoming.to_legacy()
            rows = [position[0] for position in incoming.positions]
            rows.extend(
                effective_anchor[0] + position[0]
                for position in list(figure.StartPos) + list(figure.EndPos)
            )
            rows.extend(
                effective_anchor[0] + facing[0]
                for facing in figure.EndFacing
                if isinstance(facing, (list, tuple)) and len(facing) == 2
            )
            legacy_floor.setupDanceFloorNames(int(max(rows, default=0)))
            bar_start = record.bar_range[0] if record.bar_range else 1
            crips = getCripsData(candidate, legacy_floor, bar_start=bar_start)
        except AddonValidationError as exc:
            return error(
                exc.code,
                exc.message,
                400,
                figureRef=exc.figure_ref,
                addons=list(exc.addons),
                path=exc.path,
                occurrenceId=exc.occurrence_id,
                dancers=exc.dancers,
            )
        except ExecutionError as exc:
            return error(
                exc.code,
                str(exc),
                422,
                nodeId=exc.node_id,
                path=list(exc.path),
                dancers=affected_dancers,
            )
        except (ValueError, OSError, TypeError, KeyError) as exc:
            return error("preview_failed", str(exc), 422, dancers=affected_dancers)

        return jsonify({
            "danceId": path.stem,
            "nodeId": node_id,
            "figureRef": node.figure_ref,
            "incomingFloor": serialize_floor(incoming),
            "outgoingFloor": serialize_floor(execution.outgoing_floor),
            "crips": crips,
        })

    @bp.get("/api/figures/<path:identifier>")
    def figure(identifier: str):
        repo = repository()
        try:
            definition = repo.get_legacy_definition(identifier)
        except FileNotFoundError:
            return error("not_found", "Figure was not found.", 404)
        except (ValueError, OSError) as exc:
            return error("invalid_figure", str(exc), 400)
        if definition["Version"] == 3:
            return jsonify({
                "figureRef": identifier,
                "name": definition.get("Name", identifier),
                "description": definition.get("Desc", ""),
                "version": 3,
                "capabilities": None,
            })
        try:
            capabilities = repo.get_capabilities(identifier)
        except (ValueError, OSError) as exc:
            return error("invalid_figure", str(exc), 400)
        return jsonify({
            "figureRef": capabilities.figure_ref,
            "name": definition.get("Name", identifier),
            "description": definition.get("Desc", ""),
            "version": 2,
            "capabilities": {
                "bars": capabilities.bars, "formation": capabilities.formation,
                "validAddons": list(capabilities.valid_addons),
                "supportsPreview": capabilities.supports_preview,
                "capabilityVersion": capabilities.capability_version,
                "durationAddonPattern": capabilities.duration_addon_pattern,
            },
        })

    @bp.get("/api/dances")
    def dances():
        result = []
        root = Path(app_module.DANCES_DIR)
        if root.is_dir():
            for path in sorted(root.glob("*.json")):
                try:
                    _, document, history = load(path)
                except (OSError, ValueError, TypeError):
                    continue
                result.append({
                    "id": path.stem,
                    "name": document.metadata.get(
                        "name", document.metadata.get("Name", path.stem)
                    ),
                    "revision": history.state.document.revision,
                    "incomplete": document.incomplete,
                })
        store = archive_store()
        for imported in store.list_dances():
            path = imported.path
            try:
                _, document, history = load(path)
            except (ArchiveError, OSError, ValueError, TypeError):
                continue
            result.append({
                "id": path.name,
                "name": document.metadata.get(
                    "name", document.metadata.get("Name", path.name)
                ),
                "revision": history.state.document.revision,
                "incomplete": document.incomplete,
            })
        return jsonify({"dances": result})

    def get_dance(identifier: str):
        path = resolve(identifier)
        if path is None:
            return None, None, None
        try:
            return (path, *load(path)[1:])
        except ArchiveNotFoundError:
            return None, None, None
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError(str(exc)) from exc

    @bp.get("/api/dances/<path:identifier>")
    def dance(identifier: str):
        try:
            path, document, history = get_dance(identifier)
        except ValueError as exc:
            return error("invalid_document", str(exc), 400)
        if path is None:
            return error("not_found", "Dance was not found.", 404)
        if "name" not in document.metadata:
            document = replace(
                document,
                metadata={
                    **document.metadata,
                    "name": document.metadata.get("Name", path.stem),
                },
            )
        return document_response(document, history)

    @bp.get("/api/dances/<path:identifier>/tree")
    def dance_tree(identifier: str):
        return dance(identifier)

    @bp.put("/api/dances/<path:identifier>/tree")
    def reject_tree_write(identifier: str):
        return error("method_not_allowed", "jsTree writes are not supported.", 405)

    @bp.get("/api/dances/<path:identifier>/trace")
    def trace(identifier: str):
        return dance(identifier)

    @bp.post("/api/dances/<path:identifier>/proposals")
    def proposal(identifier: str):
        try:
            path, document, history = get_dance(identifier)
            if path is None:
                return error("not_found", "Dance was not found.", 404)
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or "baseRevision" not in body or "command" not in body:
                return error("malformed_request", "baseRevision and command are required.", 400)
            command = command_from_json(body["command"])
            proposed = create_proposal(
                document, command, body["baseRevision"], history.state.repository
            )
        except (ValueError, TypeError, KeyError) as exc:
            return error("invalid_request", str(exc), 400)
        token = uuid4().hex
        proposals[token] = (cache_key(path), proposed.base_revision, proposed)
        return jsonify({"proposal": {
            "proposalId": token,
            "baseRevision": proposed.base_revision,
            "document": proposed.document.to_json(),
            "tree": proposed.structural_tree,
        }})

    @bp.post("/api/dances/<path:identifier>/apply")
    def apply(identifier: str):
        try:
            path, document, history = get_dance(identifier)
            if path is None:
                return error("not_found", "Dance was not found.", 404)
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not isinstance(body.get("proposalId"), str):
                return error("malformed_request", "proposalId is required.", 400)
            expected = expected_revision(body)
        except (ValueError, TypeError, KeyError) as exc:
            return error("invalid_request", str(exc), 400)
        key = cache_key(path)
        with dance_lock(key):
            history = histories.get(key) or load(path)[2]
            current = history.state.document
            stale = check_revision(expected, current.revision)
            if stale:
                return stale
            token_record = proposals.get(body["proposalId"])
            if (
                token_record is None
                or token_record[0] != key
                or token_record[1] != current.revision
            ):
                return error("revision_conflict", "Proposal is unknown, expired, or stale.", 409,
                             actualRevision=current.revision)
            proposed = token_record[2]
            result = apply_proposal(history.state, proposed)
            if not result.accepted:
                if result.conflict:
                    return error("revision_conflict", result.conflict.message, 409,
                                 expectedRevision=result.conflict.expected_revision,
                                 actualRevision=result.conflict.actual_revision)
                validation = result.validation.to_dict() if result.validation else None
                conflict_issue = result.validation.first_blocking if result.validation else None
                affected_dancers = list(dict.fromkeys(
                    dancer
                    for issue in (result.validation.errors if result.validation else ())
                    for dancer in issue.details.get("dancers", ())
                ))
                if conflict_issue and conflict_issue.code == "parallel_write_conflict":
                    return error("parallel_conflict", conflict_issue.message, 409,
                                 dancers=affected_dancers, validation=validation)
                return error("validation_error", "Proposal was rejected.", 400,
                             dancers=affected_dancers, validation=validation)
            committed = history.apply(proposed)
            proposals.pop(body["proposalId"], None)
            documents[key] = committed.state.document
            return document_response(committed.state.document, history)

    @bp.post("/api/dances/<path:identifier>/save")
    def save(identifier: str):
        try:
            path, current, history = get_dance(identifier)
            if path is None:
                return error("not_found", "Dance was not found.", 404)
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or "document" not in body:
                return error("malformed_request", "document is required.", 400)
            expected = expected_revision(body)
        except (ValueError, TypeError, KeyError) as exc:
            return error("invalid_request", str(exc), 400)
        key = cache_key(path)
        with dance_lock(key):
            history = histories.get(key) or load(path)[2]
            current = history.state.document
            stale = check_revision(expected, current.revision)
            if stale:
                return stale
            try:
                candidate = DanceDocument.from_json(body["document"])
            except (ValueError, TypeError, KeyError) as exc:
                return error("invalid_request", str(exc), 400)
            if candidate.revision != current.revision:
                return error(
                    "revision_conflict",
                    "Submitted document revision is stale.",
                    409,
                    expectedRevision=candidate.revision,
                    actualRevision=current.revision,
                )
            report = validate_document(
                candidate, history.state.initial_floor, history.state.repository
            )
            blocking = [
                issue for issue in report.errors
                if not (
                    candidate.incomplete
                    and issue.code == "reference_not_found"
                    and issue.details.get("figureRef") in candidate.unresolved_references
                )
            ]
            if blocking:
                return error("validation_error", "Document is invalid.", 400,
                             validation=report.to_dict())
            if (
                candidate.incomplete
                and not current.incomplete
                and not body.get("confirmIncomplete")
            ):
                return error("incomplete_confirmation_required", "Confirm incomplete draft save.", 409,
                             validation=report.to_dict())
            committed = replace(candidate, revision=current.revision + 1)
            if committed.incomplete:
                failed_execution = ExecutionResult(
                    None, None, (), tuple(report.errors), status="failed",
                    last_valid_floor=history.state.initial_floor,
                )
                new_state = EditorState(
                    committed, failed_execution, history.state.initial_floor,
                    history.state.repository,
                )
            else:
                new_state = create_state(
                    committed,
                    history.state.initial_floor,
                    history.state.repository,
                )
            try:
                persist(path, committed)
            except ArchiveCollisionError as exc:
                message = str(exc)
                if "revision is stale" in message or "replacement_revision" in message:
                    return error("revision_conflict", message, 409)
                return error("name_collision", message, 409)
            except (OSError, ValueError) as exc:
                return error("write_failed", str(exc), 500)
            if is_archive_path(path):
                persisted_revisions[key] = committed.revision
            history.save(new_state)
            histories[key] = history
            documents[key] = committed
            return document_response(committed, histories[key])

    @bp.post("/api/dances/<path:identifier>/undo")
    def undo(identifier: str):
        path, _, history = get_dance(identifier)
        if path is None:
            return error("not_found", "Dance was not found.", 404)
        try:
            body = request.get_json(silent=True)
            expected = expected_revision(body)
        except ValueError as exc:
            return error("invalid_request", str(exc), 400)
        key = cache_key(path)
        with dance_lock(key):
            history = histories.get(key) or load(path)[2]
            stale = check_revision(expected, history.state.document.revision)
            if stale:
                return stale
            try:
                state = history.undo()
            except RuntimeError as exc:
                return error("history_empty", str(exc), 409)
            documents[key] = state.document
            return document_response(state.document, history)

    @bp.post("/api/dances/<path:identifier>/redo")
    def redo(identifier: str):
        path, _, history = get_dance(identifier)
        if path is None:
            return error("not_found", "Dance was not found.", 404)
        try:
            body = request.get_json(silent=True)
            expected = expected_revision(body)
        except ValueError as exc:
            return error("invalid_request", str(exc), 400)
        key = cache_key(path)
        with dance_lock(key):
            history = histories.get(key) or load(path)[2]
            stale = check_revision(expected, history.state.document.revision)
            if stale:
                return stale
            try:
                state = history.redo()
            except RuntimeError as exc:
                return error("history_empty", str(exc), 409)
            documents[key] = state.document
            return document_response(state.document, history)

    @bp.post("/api/archives/export")
    def archive_export():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("danceId"), str):
            return error("malformed_request", "danceId is required.", 400)
        path = resolve(body["danceId"])
        if path is None:
            return error("not_found", "Dance was not found.", 404)
        if is_archive_path(path):
            key = cache_key(path)
            try:
                with dance_lock(key):
                    with archive_store().locked_snapshot(path.name) as (scoped, assets):
                        history = histories.get(key)
                        revision_floor = None
                        if history is not None and (
                            persisted_revisions.get(key) != scoped.document.revision
                        ):
                            revision_floor = history.state.document.revision
                            invalidate_dance(key)
                            history = None
                        if history is None:
                            _, _, history = _load(path, key, scoped, revision_floor)
                        archive_bytes = export_archive_bytes(
                            history.state.document,
                            scoped.repository,
                            assets=assets,
                        )
            except ArchiveNotFoundError:
                return error("not_found", "Dance was not found.", 404)
            except (ArchiveError, OSError) as exc:
                return error("archive_error", str(exc), 400)
            package = base64.b64encode(archive_bytes).decode("ascii")
            return jsonify({"package": package})
        else:
            try:
                _, document, _ = get_dance(body["danceId"])
            except ValueError as exc:
                return error("invalid_document", str(exc), 400)
            assets = {}
            figure_repository = repository()
        try:
            archive_bytes = export_archive_bytes(
                document, figure_repository, assets=assets
            )
            package = base64.b64encode(archive_bytes).decode("ascii")
        except (ArchiveError, OSError) as exc:
            return error("archive_error", str(exc), 400)
        return jsonify({"package": package})

    @bp.post("/api/archives/import")
    def archive_import():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("package"), str):
            return error("malformed_request", "package is required.", 400)
        try:
            package_bytes = base64.b64decode(body["package"], validate=True)
            package = validate_archive(package_bytes)
        except (ValueError, TypeError, ArchiveError) as exc:
            return error("archive_error", str(exc), 400)
        name = body.get("name")
        if name is not None and (
            not isinstance(name, str) or Path(name).name != name or not name.strip()
        ):
            return error("invalid_name", "Import name must be a single non-empty name.", 400)
        replacing = body.get("replace", False)
        confirm_replace = body.get("confirmReplace", False)
        if not isinstance(replacing, bool) or not isinstance(confirm_replace, bool):
            return error(
                "invalid_request",
                "replace and confirmReplace must be boolean values.",
                400,
            )
        expected = None
        store = archive_store()
        try:
            if replacing:
                expected = expected_revision(body)
                if expected is None:
                    return error("malformed_request", "Replacement requires an expected target revision.", 400)
                if not confirm_replace:
                    return error("replace_confirmation_required", "Confirm replacement.", 409)
                target_name = name or package.dance_name
                existing = store.find_by_name(target_name)
                if existing is None:
                    return error(
                        "replacement_target_not_found",
                        "Replacement target does not exist.",
                        404,
                    )
                key = cache_key(existing.path)
                with dance_lock(key):
                    _, _, history = load(existing.path)
                    stale = check_revision(expected, history.state.document.revision)
                    if stale:
                        return stale
                    imported = store.import_archive(
                        package_bytes,
                        collision="replace",
                        confirm_replace=True,
                        target_name=target_name,
                        expected_revision=existing.document.revision,
                        replacement_revision=history.state.document.revision + 1,
                    )
                    invalidate_dance(key)
            else:
                imported = store.import_archive(
                    package_bytes,
                    collision="copy",
                    copy_name=name,
                )
        except ArchiveCollisionError as exc:
            message = str(exc)
            if "revision is stale" in message:
                return error("revision_conflict", message, 409)
            if "target does not exist" in message:
                return error("replacement_target_not_found", message, 404)
            return error("name_collision", message, 409)
        except ArchiveError as exc:
            return error("archive_error", str(exc), 400)
        return jsonify({
            "danceId": imported.dance_id,
            "document": imported.document.to_json(),
            "repositoryScope": "archive",
            "packageId": imported.package_id,
        })

    return bp


def register_canonical_api(app: Any, app_module: Any) -> None:
    """Register the canonical API after legacy-only GUI routes."""
    app.register_blueprint(create_canonical_blueprint(app_module))
