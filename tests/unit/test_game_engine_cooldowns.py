# pyright: reportOptionalMemberAccess=false, reportArgumentType=false

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.events import MoveCompleted, RestCompleted, RestStarted
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.motion import ArrivalEvent
from kungfu_chess.rules.rule_engine import RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class _LeftoverArrivalArbiter:
    """Explicit collaborator that reports an arrival with a completed cooldown."""

    short_cooldown_ms = 50
    long_cooldown_ms = 100

    def __init__(self, piece: Piece) -> None:
        self._piece = piece
        self._emitted = False
        self.start_rest_calls: list[tuple[Piece, str, int]] = []

    def next_boundary_ms(self) -> None:
        return None

    def advance_time(self, ms: int) -> list[ArrivalEvent]:
        if self._emitted:
            return []
        self._emitted = True
        return [
            ArrivalEvent(
                piece=self._piece,
                source=Position(0, 0),
                destination=Position(0, 1),
                leftover_ms=ms - 100,
                original_source=Position(0, 0),
                requested_destination=Position(0, 1),
            )
        ]

    def consume_completed_rest_piece_ids(self) -> tuple[str, ...]:
        return ()

    def resolve_arrival(self, piece_id: str) -> None:
        assert piece_id == self._piece.id
        self._piece.state = "idle"

    def start_rest(self, piece: Piece, rest_kind: str, elapsed_ms: int = 0) -> None:
        self.start_rest_calls.append((piece, rest_kind, elapsed_ms))
        piece.state = "idle" if elapsed_ms >= self.long_cooldown_ms else rest_kind


class TestCooldownStateTransitions:
    """Verify move/jump arrival transitions into short_rest/long_rest and back to idle."""

    def test_move_starts_in_moving_state(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        assert board.get_piece(Position(0, 0)).state == "moving"

    def test_jump_starts_in_moving_state(self) -> None:
        engine, board = _engine([". wK ."])
        piece = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        assert piece.state == "moving"

    def test_move_arrival_transitions_to_long_rest(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1000)

        assert board.get_piece(Position(0, 1)).state == "long_rest"

    def test_jump_arrival_transitions_to_short_rest(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))

        engine.wait(1000)

        assert board.get_piece(Position(0, 1)).state == "short_rest"

    def test_long_rest_completes_exactly_after_10000ms(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        piece = board.get_piece(Position(0, 1))

        engine.wait(9999)
        assert piece.state == "long_rest"

        engine.wait(1)
        assert piece.state == "idle"

    def test_short_rest_completes_exactly_after_2000ms(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        piece = board.get_piece(Position(0, 1))

        engine.wait(1999)
        assert piece.state == "short_rest"

        engine.wait(1)
        assert piece.state == "idle"

    def test_partial_rest_remains_active(self) -> None:
        engine, _board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        engine.wait(4000)

        rests = engine.snapshot().rests
        assert len(rests) == 1
        assert rests[0].elapsed_ms == 4000
        assert rests[0].duration_ms == 10000

    def test_excessive_wait_returns_piece_to_idle(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))

        engine.wait(50000)

        assert board.get_piece(Position(0, 1)).state == "idle"
        assert engine.snapshot().rests == ()

    def test_cooldown_does_not_start_before_arrival(self) -> None:
        engine, board = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 3))

        engine.wait(500)

        assert engine.snapshot().rests == ()
        assert board.get_piece(Position(0, 0)).state == "moving"

    def test_wait_exactly_ending_at_arrival_begins_rest_with_zero_elapsed(self) -> None:
        engine, _board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1000)

        rests = engine.snapshot().rests
        assert len(rests) == 1
        assert rests[0].elapsed_ms == 0
        assert rests[0].rest_kind == "long_rest"

    def test_wait_crossing_arrival_applies_remaining_time_to_rest(self) -> None:
        engine, _board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1500)

        rests = engine.snapshot().rests
        assert rests[0].elapsed_ms == 500

    def test_wait_crossing_full_cooldown_returns_piece_to_idle(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(11000)

        assert board.get_piece(Position(0, 1)).state == "idle"
        assert engine.snapshot().rests == ()

    def test_single_large_wait_handles_motion_and_partial_cooldown(self) -> None:
        """The prompt's own example: 1000ms motion + 10000ms long cooldown."""
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(5000)

        piece = board.get_piece(Position(0, 1))
        assert piece.state == "long_rest"
        assert engine.snapshot().rests[0].elapsed_ms == 4000

    def test_single_large_wait_handles_motion_and_full_cooldown(self) -> None:
        """The prompt's own example: wait(11000) must leave the piece idle."""
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(11000)

        assert board.get_piece(Position(0, 1)).state == "idle"


class TestCooldownConcurrency:
    def test_two_pieces_rest_concurrently(self) -> None:
        engine, board = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(2, 0), Position(2, 1))

        engine.wait(1000)

        assert board.get_piece(Position(0, 1)).state == "long_rest"
        assert board.get_piece(Position(2, 1)).state == "long_rest"
        assert len(engine.snapshot().rests) == 2

    def test_one_piece_moves_while_another_rests(self) -> None:
        engine, board = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        engine.request_move(Position(2, 0), Position(2, 1))

        assert board.get_piece(Position(0, 1)).state == "long_rest"
        assert board.get_piece(Position(2, 0)).state == "moving"

    def test_different_rest_durations_advance_independently(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.jump(Position(1, 1))

        engine.wait(1000)

        mover = board.get_piece(Position(0, 1))
        jumper = board.get_piece(Position(1, 1))
        assert mover.state == "long_rest"
        assert jumper.state == "short_rest"

        engine.wait(2000)

        assert jumper.state == "idle"
        assert mover.state == "long_rest"

    def test_multiple_arrivals_in_one_wait_start_correct_rest_types(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.jump(Position(1, 1))

        engine.wait(1000)

        assert board.get_piece(Position(0, 1)).state == "long_rest"
        assert board.get_piece(Position(1, 1)).state == "short_rest"

    def test_one_large_wait_handles_several_independent_phase_boundaries(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))  # 1000ms motion, then 10000ms rest
        engine.jump(Position(1, 1))  # 1000ms motion, then 2000ms rest

        engine.wait(3000)  # both arrive at 1000ms; jumper's rest completes at 1000+2000

        mover = board.get_piece(Position(0, 1))
        jumper = board.get_piece(Position(1, 1))
        assert jumper.state == "idle"
        assert mover.state == "long_rest"
        rests = engine.snapshot().rests
        assert len(rests) == 1
        assert rests[0].piece_id == mover.id
        assert rests[0].elapsed_ms == 2000

    def test_arrival_leftover_that_completes_rest_emits_both_rest_events(
        self,
    ) -> None:
        board = parse_board(["wR ."])
        piece = board.get_piece(Position(0, 0))
        assert piece is not None
        arbiter = _LeftoverArrivalArbiter(piece)
        engine = GameEngine(board, RuleEngine(), arbiter)

        engine.wait(200)

        events = engine.consume_events()
        assert [type(event) for event in events] == [
            MoveCompleted,
            RestStarted,
            RestCompleted,
        ]
        assert arbiter.start_rest_calls == [(piece, "long_rest", 100)]
        assert piece.state == "idle"


class TestCooldownBusyRejection:
    def test_move_request_rejected_during_short_rest(self) -> None:
        engine, _board = _engine([". wK . ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        assert not result.ok
        assert result.reason == "piece_busy"

    def test_move_request_rejected_during_long_rest(self) -> None:
        engine, _board = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        assert not result.ok
        assert result.reason == "piece_busy"

    def test_jump_request_rejected_during_short_rest(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        piece_before = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        assert board.get_piece(Position(0, 1)) is piece_before
        assert piece_before.state == "short_rest"

    def test_jump_request_rejected_during_long_rest(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        piece_before = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        assert board.get_piece(Position(0, 1)) is piece_before
        assert piece_before.state == "long_rest"

    def test_action_becomes_available_immediately_after_rest_completion(self) -> None:
        engine, _board = _engine([". wK . ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        engine.wait(2000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        assert result.ok


class TestCooldownCaptures:
    def test_resting_piece_blocks_movement_paths(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        assert board.get_piece(Position(0, 2)).state == "long_rest"

        result = engine.request_move(Position(0, 3), Position(0, 0))

        assert not result.ok
        assert result.reason == "illegal_piece_move"

    def test_resting_enemy_can_be_captured(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))
        assert resting_piece.state == "long_rest"

        result = engine.request_move(Position(0, 3), Position(0, 2))
        assert result.ok

        engine.wait(1000)

        assert resting_piece.state == "captured"
        capturer = board.get_piece(Position(0, 2))
        assert capturer is not None
        assert capturer.color == "b"

    def test_capturing_a_resting_piece_removes_its_rest_record(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))
        assert len(engine.snapshot().rests) == 1

        engine.request_move(Position(0, 3), Position(0, 2))
        engine.wait(1000)

        # The captured piece's own rest record is gone; the capturing piece
        # (which survives and now starts its own long_rest) is unaffected.
        assert resting_piece.id not in {
            rest.piece_id for rest in engine.snapshot().rests
        }
        assert resting_piece.id not in {p.id for p in engine.snapshot().pieces}

    def test_captured_resting_piece_never_returns_to_idle(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))

        engine.request_move(Position(0, 3), Position(0, 2))
        engine.wait(1000)
        assert resting_piece.state == "captured"

        engine.wait(50000)

        assert resting_piece.state == "captured"

    def test_moving_piece_captured_during_arrival_does_not_enter_rest(self) -> None:
        engine, board = _engine(["wR . . .", "bR . . ."])
        captured_mover = board.get_piece(Position(0, 0))

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.request_move(Position(0, 0), Position(0, 3))

        engine.wait(1000)

        assert captured_mover.state == "captured"
        assert captured_mover.id not in {
            rest.piece_id for rest in engine.snapshot().rests
        }

    def test_move_capture_causes_long_rest_for_surviving_mover(self) -> None:
        engine, board = _engine(["wR . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        survivor = board.get_piece(Position(0, 2))
        assert survivor.color == "w"
        assert survivor.state == "long_rest"

    def test_jump_capture_causes_short_rest_for_surviving_jumper(self) -> None:
        engine, board = _engine([". . .", "wP bR .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))

        engine.wait(1000)

        jumper = board.get_piece(Position(1, 0))
        assert jumper.color == "w"
        assert jumper.state == "short_rest"
