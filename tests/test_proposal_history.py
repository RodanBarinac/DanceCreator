import pytest

from src.engine.domain.dance_model import DanceDocument, FigureOccurrence, GroupNode
from src.engine.editing.commands import InsertOccurrence, ReorderNode, UpdateAddons
from src.engine.editing.history import History
from src.engine.editing.proposals import create_proposal
from src.engine.editing.state import create_state
from src.engine.execution.combine import FloorEntry, FloorState
from src.engine.figures.capabilities import FigureRepository


def _document():
    return DanceDocument(
        1,
        {"name": "history"},
        GroupNode(
            "root",
            "series",
            (FigureOccurrence("first", "1cWait", (1, 0), ()),),
        ),
    )


def _floor():
    return FloorState(
        {
            (1, -1): FloorEntry("M1", "male", (1, 1)),
            (1, 1): FloorEntry("W1", "female", (1, -1)),
        }
    )


def _setup():
    repository = FigureRepository()
    state = create_state(_document(), _floor(), repository)
    return History(state)


def test_apply_commits_document_and_execution_trace_once_and_increments_revision():
    history = _setup()
    proposal = create_proposal(
        history.state.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        history.state.document.revision,
        repository=history.state.repository,
    )
    old_document = history.state.document
    old_execution = history.state.execution_result

    result = history.apply(proposal)

    assert result.accepted is True
    assert result.state is history.state
    assert result.state.document.revision == old_document.revision + 1
    assert len(result.state.document.root.children) == 2
    assert result.state.execution_result is not old_execution
    assert result.state.execution_result.trace_records
    assert history.undo_depth == 1
    assert history.redo_depth == 0


def test_cancel_is_a_noop_and_never_enters_history():
    history = _setup()
    state = history.state
    proposal = create_proposal(
        state.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        state.document.revision,
        repository=state.repository,
    )

    history.cancel(proposal)

    assert history.state is state
    assert history.state.document is state.document
    assert history.state.execution_result is state.execution_result
    assert history.undo_depth == history.redo_depth == 0


def test_applied_composite_proposal_preserves_generated_tree_ids(monkeypatch):
    history = _setup()
    repository = history.state.repository
    figure_exists = repository.figure_exists
    get_legacy_definition = repository.get_legacy_definition
    monkeypatch.setattr(
        repository,
        "figure_exists",
        lambda figure_ref: figure_ref == "SyntheticV3" or figure_exists(figure_ref),
    )
    monkeypatch.setattr(
        repository,
        "get_legacy_definition",
        lambda figure_ref: (
            {
                "Version": 3,
                "FigureList": ["s", [[[0, 0], "1cWait"]]],
            }
            if figure_ref == "SyntheticV3"
            else get_legacy_definition(figure_ref)
        ),
    )

    proposal = create_proposal(
        history.state.document,
        InsertOccurrence("root", "SyntheticV3", 1, anchor=(1, 0)),
        history.state.document.revision,
        repository=repository,
    )
    proposed = proposal.candidate.root.children[1]
    proposed_root = proposed.root
    proposed_child = proposed_root.children[0]

    result = history.apply(proposal)

    assert result.accepted is True
    applied = result.state.document.root.children[1]
    assert applied.id == proposed.id
    assert applied.root.id == proposed_root.id
    assert applied.root.children[0].id == proposed_child.id


def test_invalid_composite_addons_are_preserved_then_rejected_on_apply(monkeypatch):
    history = _setup()
    repository = history.state.repository
    figure_exists = repository.figure_exists
    get_legacy_definition = repository.get_legacy_definition
    monkeypatch.setattr(
        repository,
        "figure_exists",
        lambda figure_ref: figure_ref == "SyntheticV3" or figure_exists(figure_ref),
    )
    monkeypatch.setattr(
        repository,
        "get_legacy_definition",
        lambda figure_ref: (
            {
                "Version": 3,
                "FigureList": ["s", [[[0, 0], "1cWait"]]],
            }
            if figure_ref == "SyntheticV3"
            else get_legacy_definition(figure_ref)
        ),
    )
    state = history.state
    proposal = create_proposal(
        state.document,
        InsertOccurrence("root", "SyntheticV3", 1, anchor=(1, 0), addons=("unsupported",)),
        state.document.revision,
        repository=repository,
    )

    assert proposal.candidate.root.children[1].addons == ("unsupported",)
    result = history.apply(proposal)

    assert result.accepted is False
    assert result.rejection.first_blocking.code == "unsupported_addon"
    assert history.state is state


def test_proposal_rejects_mismatched_source_revision():
    document = _document()

    with pytest.raises(ValueError, match="must match the source document"):
        create_proposal(
            document,
            InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
            document.revision + 1,
        )


def test_proposal_candidate_and_projection_cannot_mutate_source_or_snapshot():
    history = _setup()
    document = history.state.document
    before = document.to_json()
    proposal = create_proposal(
        document,
        ReorderNode("first", 0),
        document.revision,
    )

    proposal.candidate.metadata["name"] = "mutated"
    proposal.structural_tree["children"].clear()

    assert document.to_json() == before
    assert proposal.candidate.metadata == before["metadata"]
    assert proposal.structural_tree["children"]


def test_invalid_candidate_is_rejected_without_changing_state_or_history():
    history = _setup()
    state = history.state
    proposal = create_proposal(
        state.document,
        UpdateAddons("first", ("unknown-addon",)),
        state.document.revision,
    )

    result = history.apply(proposal)

    assert result.accepted is False
    assert result.rejection.errors[0].code == "unsupported_addon"
    assert history.state is state
    assert history.state.document is state.document
    assert history.state.execution_result is state.execution_result
    assert history.state.document.revision == state.document.revision
    assert history.undo_depth == history.redo_depth == 0


def test_stale_proposal_returns_structured_conflict_without_mutation():
    history = _setup()
    state = history.state
    stale_proposal = create_proposal(
        state.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        base_revision=state.document.revision,
        repository=state.repository,
    )
    current_proposal = create_proposal(
        state.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        base_revision=state.document.revision,
        repository=state.repository,
    )
    history.apply(current_proposal)
    current = history.state

    result = history.apply(stale_proposal)

    assert result.accepted is False
    assert result.conflict.code == "revision_conflict"
    assert result.conflict.expected_revision == state.document.revision
    assert result.conflict.actual_revision == current.document.revision
    assert history.state is current
    assert history.undo_depth == 1
    assert history.redo_depth == 0


def test_undo_redo_restore_semantics_and_exact_trace_with_fresh_monotonic_revisions():
    history = _setup()
    initial = history.state
    proposal = create_proposal(
        initial.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        initial.document.revision,
        repository=history.state.repository,
    )
    applied = history.apply(proposal).state
    high_revision = applied.document.revision

    undone = history.undo()
    assert undone.document.to_json()["root"] == initial.document.to_json()["root"]
    assert undone.execution_result is initial.execution_result
    assert undone.document.revision == high_revision + 1

    redone = history.redo()
    assert redone.document.to_json()["root"] == applied.document.to_json()["root"]
    assert redone.execution_result is applied.execution_result
    assert redone.document.revision == undone.document.revision + 1


def test_new_apply_after_undo_clears_redo_and_uses_next_revision():
    history = _setup()
    initial = history.state
    first = create_proposal(
        initial.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        initial.document.revision,
        repository=history.state.repository,
    )
    history.apply(first)
    history.undo()
    revision = history.state.document.revision

    second = create_proposal(
        history.state.document,
        InsertOccurrence("root", "1cWait", 1, anchor=(1, 0)),
        revision,
        repository=history.state.repository,
    )
    result = history.apply(second)

    assert result.accepted is True
    assert result.state.document.revision == revision + 1
    assert history.redo_depth == 0
    with pytest.raises(RuntimeError, match="redo"):
        history.redo()
