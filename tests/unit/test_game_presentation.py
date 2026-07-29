from __future__ import annotations

import pytest

from kungfu_chess.model.events import (
    JumpCompleted,
    JumpStarted,
    MoveCompleted,
    MoveStarted,
    PieceCaptured,
    PiecePromoted,
    RestCompleted,
)
from kungfu_chess.model.position import Position
from kungfu_chess.ui.presentation import (
    GamePresentation,
)

PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}


def _presentation() -> GamePresentation:
    return GamePresentation(PIECE_VALUES, board_height=8)


def _capture(
    kind: str,
    *,
    captured_id: str | None = None,
    by_id: str = "white_piece",
    by_color: str = "w",
    captured_color: str = "b",
) -> PieceCaptured:
    return PieceCaptured(
        captured_piece_id=captured_id or f"captured_{kind}",
        captured_piece_kind=kind,
        captured_piece_color=captured_color,
        by_piece_id=by_id,
        by_piece_color=by_color,
        position=Position(4, 7),
    )


def _move(
    piece_id: str = "white_rook",
    *,
    kind: str = "R",
    color: str = "w",
    source: Position = Position(7, 4),
    destination: Position = Position(4, 4),
) -> MoveCompleted:
    return MoveCompleted(
        piece_id=piece_id,
        piece_kind=kind,
        piece_color=color,
        source=source,
        destination=destination,
    )


def test_non_positive_board_height_is_rejected() -> None:
    with pytest.raises(ValueError, match="board_height"):
        GamePresentation(PIECE_VALUES, board_height=0)


def test_scores_start_at_zero() -> None:
    snapshot = _presentation().snapshot()

    assert snapshot.white_score == 0
    assert snapshot.black_score == 0


@pytest.mark.parametrize(
    ("kind", "expected_value"),
    tuple(PIECE_VALUES.items()),
)
def test_capturing_each_piece_kind_adds_its_configured_value(
    kind: str, expected_value: int
) -> None:
    presentation = _presentation()

    presentation.apply((_capture(kind),))

    assert presentation.snapshot().white_score == expected_value


def test_score_is_awarded_to_explicit_capturing_color() -> None:
    presentation = _presentation()

    presentation.apply(
        (
            _capture(
                "Q",
                by_id="black_rook",
                by_color="b",
                captured_color="b",
            ),
        )
    )

    snapshot = presentation.snapshot()
    assert snapshot.white_score == 0
    assert snapshot.black_score == PIECE_VALUES["Q"]


def test_capture_with_unsupported_capturing_color_is_rejected() -> None:
    presentation = _presentation()

    with pytest.raises(ValueError, match="capturing piece color"):
        presentation.apply((_capture("P", by_color="x"),))

    assert presentation.snapshot().white_score == 0
    assert presentation.snapshot().black_score == 0


def test_capture_requires_a_configured_piece_value() -> None:
    presentation = _presentation()

    with pytest.raises(ValueError, match="Missing configured value"):
        presentation.apply((_capture("X"),))

    assert presentation.snapshot().white_score == 0
    assert presentation.snapshot().black_score == 0


def test_same_capture_event_is_counted_exactly_once() -> None:
    presentation = _presentation()
    capture = _capture("R")

    presentation.apply((capture, capture, _move()))

    assert presentation.snapshot().white_score == PIECE_VALUES["R"]


def test_normal_completed_move_uses_dash_and_board_coordinates() -> None:
    presentation = _presentation()

    presentation.apply((_move(),))

    assert presentation.snapshot().white_actions[0].notation == "R e1-e4"


def test_capturing_move_and_jump_use_x() -> None:
    presentation = _presentation()
    jump = JumpCompleted(
        piece_id="black_knight",
        piece_kind="N",
        piece_color="b",
        source=Position(4, 4),
        destination=Position(4, 4),
    )

    presentation.apply(
        (
            _capture("P", by_id="white_rook"),
            _move(),
            _capture("B", by_id="black_knight", by_color="b"),
            jump,
        )
    )

    snapshot = presentation.snapshot()
    assert snapshot.white_actions[0].notation == "R e1xe4"
    assert snapshot.black_actions[0].notation == "N e4xe4 (jump)"


def test_non_capturing_jump_has_explicit_jump_label() -> None:
    presentation = _presentation()

    presentation.apply(
        (
            JumpCompleted(
                piece_id="white_knight",
                piece_kind="N",
                piece_color="w",
                source=Position(4, 4),
                destination=Position(4, 4),
            ),
        )
    )

    assert presentation.snapshot().white_actions[0].notation == "N e4 (jump)"


def test_friendly_early_stop_logs_actual_stopping_cell() -> None:
    presentation = _presentation()

    presentation.apply(
        (
            _move(
                source=Position(7, 0),
                destination=Position(5, 0),
            ),
        )
    )

    assert presentation.snapshot().white_actions[0].notation == "R a1-a3"


def test_promotion_appends_promoted_kind() -> None:
    presentation = _presentation()
    move = _move(
        piece_id="white_pawn",
        kind="P",
        source=Position(1, 4),
        destination=Position(0, 4),
    )

    presentation.apply((move, PiecePromoted("white_pawn", "Q")))

    assert presentation.snapshot().white_actions[0].notation == "P e7-e8=Q"


def test_promotion_without_a_completed_action_leaves_histories_unchanged() -> None:
    presentation = _presentation()

    presentation.apply((PiecePromoted("unknown_piece", "Q"),))

    snapshot = presentation.snapshot()
    assert snapshot.white_actions == ()
    assert snapshot.black_actions == ()


def test_promotion_updates_the_latest_matching_action_not_the_latest_action() -> None:
    presentation = _presentation()
    pawn_move = _move(piece_id="white_pawn", kind="P")
    later_rook_move = _move(piece_id="white_rook")

    presentation.apply(
        (pawn_move, later_rook_move, PiecePromoted("white_pawn", "Q"))
    )

    actions = presentation.snapshot().white_actions
    assert actions[0].notation.endswith("=Q")
    assert not actions[1].notation.endswith("=Q")


def test_started_intermediate_rest_and_rejected_requests_create_no_log_entry() -> None:
    presentation = _presentation()

    presentation.apply(
        (
            MoveStarted("white_rook", Position(7, 0), Position(4, 0)),
            JumpStarted("black_knight", Position(3, 3), Position(3, 3)),
            RestCompleted("white_rook"),
        )
    )
    presentation.apply(())  # A rejected request emits no event.

    snapshot = presentation.snapshot()
    assert snapshot.white_actions == ()
    assert snapshot.black_actions == ()


def test_complete_histories_are_preserved_independently_for_each_color() -> None:
    presentation = _presentation()
    white_count = 7
    black_count = 8
    white_moves = tuple(
        _move(
            piece_id=f"white_rook_{index}",
            source=Position(7, index % 8),
            destination=Position(6, index % 8),
        )
        for index in range(white_count)
    )
    black_moves = tuple(
        _move(
            piece_id=f"black_rook_{index}",
            color="b",
            source=Position(0, index % 8),
            destination=Position(1, index % 8),
        )
        for index in range(black_count)
    )

    presentation.apply(white_moves + black_moves)

    snapshot = presentation.snapshot()
    assert len(snapshot.white_actions) == white_count
    assert len(snapshot.black_actions) == black_count
    assert snapshot.white_actions[0].piece_id == "white_rook_0"
    assert snapshot.white_actions[-1].piece_id == "white_rook_6"
    assert snapshot.black_actions[0].piece_id == "black_rook_0"
    assert snapshot.black_actions[-1].piece_id == "black_rook_7"
