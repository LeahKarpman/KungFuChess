# pyright: reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.events import (
    GameOver,
    JumpCompleted,
    JumpStarted,
    MoveCompleted,
    MoveStarted,
    PieceCaptured,
    PiecePromoted,
    RestCompleted,
    RestStarted,
)
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.ui.presentation import GamePresentation


def _engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board


def test_intermediate_king_capture_completes_and_logs_winning_move() -> None:
    engine, board = _engine(["wR . . .", ". . bK ."])
    engine.request_move(Position(0, 0), Position(0, 3))
    engine.consume_events()
    engine.wait(500)
    engine.request_move(Position(1, 2), Position(0, 2))
    engine.consume_events()
    engine.wait(1000)
    engine.consume_events()

    engine.wait(500)
    events = engine.consume_events()

    assert events == (
        PieceCaptured(
            captured_piece_id="bK_1_2",
            captured_piece_kind="K",
            captured_piece_color="b",
            by_piece_id="wR_0_0",
            by_piece_color="w",
            position=Position(0, 2),
        ),
        MoveCompleted(
            piece_id="wR_0_0",
            piece_kind="R",
            piece_color="w",
            source=Position(0, 0),
            destination=Position(0, 2),
        ),
        GameOver(winner_color="w"),
    )
    assert not any(isinstance(event, RestStarted) for event in events)
    assert board.get_piece(Position(0, 2)).id == "wR_0_0"
    assert engine.snapshot().motions == ()

    presentation = GamePresentation(
        {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0},
        board_height=2,
    )
    presentation.apply(events)

    assert tuple(entry.notation for entry in presentation.snapshot().white_actions) == (
        "R a2xc2",
    )
    assert presentation.snapshot().black_actions == ()


class TestEventCreation:
    def test_move_produces_move_started_and_move_completed(self) -> None:
        engine, _ = _engine(["wR . ."])

        engine.request_move(Position(0, 0), Position(0, 1))
        started_events = engine.consume_events()

        engine.wait(1000)
        completed_events = engine.consume_events()

        assert started_events == (
            MoveStarted("wR_0_0", Position(0, 0), Position(0, 1)),
        )
        assert (
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
            in completed_events
        )

    def test_jump_produces_jump_started_and_jump_completed(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))
        started_events = engine.consume_events()

        engine.wait(1000)
        completed_events = engine.consume_events()

        assert started_events == (
            JumpStarted("wK_0_1", Position(0, 1), Position(0, 1)),
        )
        assert (
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            )
            in completed_events
        )

    def test_capture_produces_piece_captured(self) -> None:
        """Also covers: normal PieceCaptured exposes id/kind/color/attacker/position."""
        engine, _ = _engine(["wR . bR"])

        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        events = engine.consume_events()
        assert (
            PieceCaptured(
                captured_piece_id="bR_0_2",
                captured_piece_kind="R",
                captured_piece_color="b",
                by_piece_id="wR_0_0",
                by_piece_color="w",
                position=Position(0, 2),
            )
            in events
        )

    def test_promotion_produces_piece_promoted(self) -> None:
        engine, _ = _engine([".", "wP"])

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        events = engine.consume_events()
        assert PiecePromoted(piece_id="wP_1_0", new_kind="Q") in events

    def test_move_produces_rest_started(self) -> None:
        engine, _ = _engine(["wR . ."])

        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        events = engine.consume_events()
        assert (
            RestStarted(piece_id="wR_0_0", rest_kind="long_rest", duration_ms=10000)
            in events
        )

    def test_rest_completion_produces_rest_completed(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        engine.consume_events()

        engine.wait(10000)
        events = engine.consume_events()

        assert RestCompleted(piece_id="wR_0_0") in events

    def test_king_capture_produces_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])

        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        events = engine.consume_events()
        assert GameOver(winner_color="w") in events


class TestEventOrdering:
    def test_move_completed_happens_before_rest_started(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
        )
        rest_started_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, RestStarted)
        )
        assert move_completed_index < rest_started_index

    def test_rest_started_happens_before_rest_completed_on_immediate_completion(
        self,
    ) -> None:
        """The prompt's own example: motion completes, rest starts, rest completes — one wait()."""
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(
            11000
        )  # 1000ms motion + the full 10000ms long_rest in a single call
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
        )
        rest_started_index = events.index(
            RestStarted(piece_id="wR_0_0", rest_kind="long_rest", duration_ms=10000)
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wR_0_0"))

        assert move_completed_index < rest_started_index
        assert rest_started_index < rest_completed_index

    def test_events_emitted_in_correct_chronological_order(self) -> None:
        engine, _ = _engine([".", "wP"])
        engine.request_move(Position(1, 0), Position(0, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wP_1_0",
                piece_kind="P",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(0, 0),
            )
        )
        promoted_index = events.index(PiecePromoted(piece_id="wP_1_0", new_kind="Q"))
        rest_started_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, RestStarted)
        )

        assert move_completed_index < promoted_index
        assert promoted_index < rest_started_index


class TestEventTiming:
    def test_wait_crossing_motion_boundary_produces_correct_sequence(self) -> None:
        engine, _ = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 3))  # 3-cell move, 3000ms
        engine.consume_events()

        engine.wait(1500)  # still mid-flight
        mid_flight_events = engine.consume_events()
        assert mid_flight_events == ()

        engine.wait(1500)  # now arrives at 3000ms total
        arrival_events = engine.consume_events()
        assert (
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 3),
            )
            in arrival_events
        )

    def test_wait_crossing_rest_boundary_produces_rest_completed(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)  # short_rest starts (2000ms)
        engine.consume_events()

        engine.wait(1000)  # rest still active
        mid_rest_events = engine.consume_events()
        assert mid_rest_events == ()

        engine.wait(1000)  # rest completes (total elapsed 2000ms)
        completed_events = engine.consume_events()
        assert RestCompleted(piece_id="wK_0_1") in completed_events


class TestEventConcurrency:
    def test_multiple_pieces_produce_independent_events(self) -> None:
        engine, _ = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(2, 0), Position(2, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert (
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
            in events
        )
        assert (
            MoveCompleted(
                piece_id="bR_2_0",
                piece_kind="R",
                piece_color="b",
                source=Position(2, 0),
                destination=Position(2, 1),
            )
            in events
        )

    def test_event_order_is_deterministic_across_runs(self) -> None:
        def _run() -> tuple:
            engine, _ = _engine(["wR . .", ". . .", "bR . ."])
            engine.request_move(Position(0, 0), Position(0, 1))
            engine.request_move(Position(2, 0), Position(2, 1))
            engine.consume_events()
            engine.wait(1000)
            return engine.consume_events()

        assert _run() == _run()


class TestChronologicalBoundaryOrdering:
    """A single wait() may cross several boundaries; each must resolve in
    simulated-time order, since an earlier arrival can cancel or start a
    later completion (e.g. a capture cancelling a resting piece's cooldown).
    """

    def test_motion_completing_before_existing_rest_orders_move_completed_first(
        self,
    ) -> None:
        engine, _ = _engine(["wK . . .", ". . . .", "wR . . .", ". . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(2, 0), Position(2, 1))  # 1-cell move, 1000ms
        engine.consume_events()

        engine.wait(2000)  # move arrives at 1000ms; king's rest completes at 2000ms
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_2_0",
                piece_kind="R",
                piece_color="w",
                source=Position(2, 0),
                destination=Position(2, 1),
            )
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        assert move_completed_index < rest_completed_index

    def test_existing_rest_completing_before_motion_orders_rest_completed_first(
        self,
    ) -> None:
        engine, _ = _engine(["wK . . .", "wR . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(1, 3))  # 3-cell move, 3000ms
        engine.consume_events()

        engine.wait(3000)  # king's rest completes at 2000ms; move arrives at 3000ms
        events = engine.consume_events()

        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_1_0",
                piece_kind="R",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 3),
            )
        )
        assert rest_completed_index < move_completed_index

    def test_capturing_resting_piece_cancels_its_rest_without_rest_completed(
        self,
    ) -> None:
        engine, _ = _engine(["wR . .", "bR . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(0, 0))  # captures at 1000ms
        engine.consume_events()

        engine.wait(
            2000
        )  # spans the capture (1000ms) and the rest's original 2000ms deadline
        events = engine.consume_events()

        assert (
            PieceCaptured(
                captured_piece_id="wR_0_0",
                captured_piece_kind="R",
                captured_piece_color="w",
                by_piece_id="bR_1_0",
                by_piece_color="b",
                position=Position(0, 0),
            )
            in events
        )
        assert not (
            any(
                (
                    isinstance(event, RestCompleted) and event.piece_id == "wR_0_0"
                    for event in events
                )
            )
        )

        snapshot = engine.snapshot()
        assert not (any((rest.piece_id == "wR_0_0" for rest in snapshot.rests)))
        assert not (any((piece.id == "wR_0_0" for piece in snapshot.pieces)))

    def test_rest_and_motion_completing_at_same_millisecond_use_tie_rule(self) -> None:
        engine, _ = _engine(["wK . . .", "wR . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(1, 2))  # 2-cell move, 2000ms
        engine.consume_events()

        engine.wait(
            2000
        )  # rest and move both complete at the same simulated millisecond
        events = engine.consume_events()

        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_1_0",
                piece_kind="R",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 2),
            )
        )
        assert rest_completed_index < move_completed_index

    def test_two_motions_and_two_rests_completing_at_different_boundaries_stay_ordered(
        self,
    ) -> None:
        board = parse_board(["wK . . .", "wR . . .", "wR . . .", "wR . . ."])
        arbiter = RealTimeArbiter(short_cooldown_ms=500, long_cooldown_ms=4000)
        engine = GameEngine(board, RuleEngine(), arbiter)

        engine.jump(Position(0, 0))  # king: jump, then short_rest(500ms)
        engine.request_move(
            Position(1, 0), Position(1, 1)
        )  # piece D: 1-cell, completes with the jump
        engine.consume_events()

        engine.wait(
            1000
        )  # jump + D's move complete; king's rest(500ms) and D's rest(4000ms) start
        engine.consume_events()

        engine.request_move(
            Position(2, 0), Position(2, 1)
        )  # piece B: 1-cell, 1000ms from now
        engine.request_move(
            Position(3, 0), Position(3, 3)
        )  # piece C: 3-cell, 3000ms from now
        engine.consume_events()

        engine.wait(
            4000
        )  # boundaries at 500 (king rest), 1000 (B), 3000 (C), 4000 (D rest)
        events = engine.consume_events()

        rest_a_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_b_index = events.index(
            MoveCompleted(
                piece_id="wR_2_0",
                piece_kind="R",
                piece_color="w",
                source=Position(2, 0),
                destination=Position(2, 1),
            )
        )
        move_c_index = events.index(
            MoveCompleted(
                piece_id="wR_3_0",
                piece_kind="R",
                piece_color="w",
                source=Position(3, 0),
                destination=Position(3, 3),
            )
        )
        rest_d_index = events.index(RestCompleted(piece_id="wR_1_0"))

        assert rest_a_index < move_b_index
        assert move_b_index < move_c_index
        assert move_c_index < rest_d_index

    def test_jump_arrival_starting_rest_that_completes_within_same_wait(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.consume_events()

        engine.wait(3000)  # 1000ms jump + the full 2000ms short_rest, in one call
        events = engine.consume_events()

        jump_completed_index = events.index(
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            )
        )
        rest_started_index = events.index(
            RestStarted(piece_id="wK_0_1", rest_kind="short_rest", duration_ms=2000)
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_1"))

        assert jump_completed_index < rest_started_index
        assert rest_started_index < rest_completed_index

    def test_capturing_resting_king_produces_game_over_without_rest_completed(
        self,
    ) -> None:
        engine, _ = _engine(["bK . .", "wR . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(0, 0))  # captures at 1000ms
        engine.consume_events()

        engine.wait(
            2000
        )  # spans the capture (1000ms) and the rest's original 2000ms deadline
        events = engine.consume_events()

        assert (
            PieceCaptured(
                captured_piece_id="bK_0_0",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wR_1_0",
                by_piece_color="w",
                position=Position(0, 0),
            )
            in events
        )
        assert GameOver(winner_color="w") in events
        assert not (
            any(
                (
                    isinstance(event, RestCompleted) and event.piece_id == "bK_0_0"
                    for event in events
                )
            )
        )
        assert engine.game_over


class TestApprovedCaptureEventOrder:
    """Approved order: PieceCaptured, MoveCompleted/JumpCompleted, PiecePromoted
    (when relevant), GameOver (when relevant), RestStarted (unless game over
    prevents rest).
    """

    def test_move_king_capture_exact_order(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.consume_events()

        engine.wait(2000)
        events = engine.consume_events()

        assert events == (
            PieceCaptured(
                captured_piece_id="bK_0_2",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wR_0_0",
                by_piece_color="w",
                position=Position(0, 2),
            ),
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 2),
            ),
            GameOver(winner_color="w"),
        )

    def test_jump_king_capture_exact_order(self) -> None:
        """A jump always lands back on its own source cell, so the only way it
        captures a king is if the king moves into that vacated cell while the
        jumper is airborne — the same landing-reservation mechanism already
        exercised by TestLandingReservation. The king's own (harmless) move
        into the empty cell therefore resolves first, ahead of the three
        events under test here.
        """
        engine, _ = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        captured_index = events.index(
            PieceCaptured(
                captured_piece_id="bK_1_1",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wP_1_0",
                by_piece_color="w",
                position=Position(1, 0),
            )
        )
        jump_completed_index = events.index(
            JumpCompleted(
                piece_id="wP_1_0",
                piece_kind="P",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 0),
            )
        )
        game_over_index = events.index(GameOver(winner_color="w"))

        assert captured_index < jump_completed_index
        assert jump_completed_index < game_over_index
        assert not (
            any(
                (
                    isinstance(event, RestStarted) and event.piece_id == "wP_1_0"
                    for event in events
                )
            )
        )

    def test_capture_promotion_and_game_over_exact_order(self) -> None:
        engine, _ = _engine(["bK . .", ". wP ."])
        engine.request_move(Position(1, 1), Position(0, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert events == (
            PieceCaptured(
                captured_piece_id="bK_0_0",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wP_1_1",
                by_piece_color="w",
                position=Position(0, 0),
            ),
            MoveCompleted(
                piece_id="wP_1_1",
                piece_kind="P",
                piece_color="w",
                source=Position(1, 1),
                destination=Position(0, 0),
            ),
            PiecePromoted(piece_id="wP_1_1", new_kind="Q"),
            GameOver(winner_color="w"),
        )

    def test_promoted_pawn_captured_later_reports_current_kind(self) -> None:
        engine, _ = _engine([". . .", "wP . .", "bR . ."])
        engine.request_move(Position(1, 0), Position(0, 0))  # promotes to Q
        engine.wait(1000)
        engine.consume_events()

        engine.request_move(Position(2, 0), Position(0, 0))  # rook captures the queen
        engine.consume_events()

        engine.wait(2000)
        events = engine.consume_events()

        assert (
            PieceCaptured(
                captured_piece_id="wP_1_0",
                captured_piece_kind="Q",
                captured_piece_color="w",
                by_piece_id="bR_2_0",
                by_piece_color="b",
                position=Position(0, 0),
            )
            in events
        )

    def test_move_completed_contains_full_payload(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert (
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
            in events
        )

    def test_jump_completed_contains_full_payload(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert (
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            )
            in events
        )

    def test_simultaneous_king_captures_first_arrival_wins(self) -> None:
        """Both rooks capture the enemy king in one cell, arriving at the same
        simulated millisecond; only the sequence tie-break (white scheduled
        first) may decide the winner — see RealTimeArbiter's deterministic
        arrival ordering.
        """
        engine, board = _engine(["wK bR", "bK wR"])
        engine.request_move(
            Position(1, 1), Position(1, 0)
        )  # white rook: scheduled first
        engine.request_move(
            Position(0, 1), Position(0, 0)
        )  # black rook: scheduled second
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert events == (
            PieceCaptured(
                captured_piece_id="bK_1_0",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wR_1_1",
                by_piece_color="w",
                position=Position(1, 0),
            ),
            MoveCompleted(
                piece_id="wR_1_1",
                piece_kind="R",
                piece_color="w",
                source=Position(1, 1),
                destination=Position(1, 0),
            ),
            GameOver(winner_color="w"),
        )

        white_king = board.get_piece(Position(0, 0))
        assert white_king is not None
        assert white_king.state != "captured"
        assert engine.game_over

    def test_no_rest_started_emitted_after_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        events = engine.consume_events()

        game_over_index = events.index(GameOver(winner_color="w"))
        assert not (any((isinstance(event, RestStarted) for event in events)))
        assert not (
            any((isinstance(event, RestStarted) for event in events[game_over_index:]))
        )

    def test_gameover_is_final_event_emitted(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)
        events = engine.consume_events()

        assert isinstance(events[-1], GameOver)

    def test_exactly_one_gameover_event_for_simultaneous_king_captures(self) -> None:
        engine, _ = _engine(["wK bR", "bK wR"])
        engine.request_move(Position(1, 1), Position(1, 0))
        engine.request_move(Position(0, 1), Position(0, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        assert sum((1 for e in events if isinstance(e, GameOver))) == 1


class TestGameOverEventFreeze:
    """Verify that no public event of any kind is emitted once a wait()
    call has already ended the game — including in a later, separate
    wait() call that would otherwise complete an action left in flight.
    """

    def test_no_restcompleted_emitted_in_later_wait_after_game_over(self) -> None:
        engine, _ = _engine(["wR . bK", "wR . ."])
        engine.request_move(Position(1, 0), Position(1, 1))
        engine.wait(1000)  # second rook arrives and starts a 10000ms long_rest
        engine.consume_events()

        engine.request_move(Position(0, 0), Position(0, 2))  # captures king in 2000ms
        engine.wait(2000)
        assert engine.game_over
        engine.consume_events()

        engine.wait(
            20000
        )  # would finish wN's rest (8000ms left) if the bug were present
        events = engine.consume_events()

        assert events == ()
        assert not (any((isinstance(e, RestCompleted) for e in events)))

    def test_no_movecompleted_emitted_in_later_wait_after_game_over(self) -> None:
        engine, _ = _engine(["bK wR . . . wN", ". . . . . ."])
        engine.request_move(Position(0, 5), Position(1, 3))  # knight, 3000ms
        engine.request_move(
            Position(0, 1), Position(0, 0)
        )  # rook captures king, 1000ms
        engine.consume_events()

        engine.wait(1000)
        assert engine.game_over
        engine.consume_events()

        engine.wait(
            10000
        )  # would finish the knight's move (2000ms left) if the bug were present
        events = engine.consume_events()

        assert events == ()


class TestEventImmutability:
    def test_events_are_immutable(self) -> None:
        event = MoveStarted(
            piece_id="wR_0_0", source=Position(0, 0), destination=Position(0, 1)
        )

        with pytest.raises(AttributeError):
            setattr(event, "piece_id", "changed")  # noqa: B010

    def test_consume_events_clears_internal_queue(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        first_call = engine.consume_events()
        second_call = engine.consume_events()

        assert len(first_call) > 0
        assert second_call == ()

    def test_returned_event_tuple_is_not_mutable(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        events = engine.consume_events()

        with pytest.raises(AttributeError):
            getattr(events, "append")(  # noqa: B009
                MoveStarted("x", Position(0, 0), Position(0, 1))
            )
