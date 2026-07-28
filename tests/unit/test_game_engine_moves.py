# pyright: reportOptionalMemberAccess=false

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.events import MoveCompleted, PieceCaptured, RestStarted
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import MoveValidation, RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class _FalseyRuleEngine(RuleEngine):
    """Expose whether a falsey injected validation service is actually used."""

    def __bool__(self) -> bool:
        return False

    def validate_move(
        self,
        board: Board,
        src: Position,
        dst: Position,
    ) -> MoveValidation:
        return MoveValidation(ok=False, reason="injected_rule_engine")


class _FailingMoveRules:
    def validate_move(self, board, src, dst):
        raise AssertionError("validate_move must not be called")


class _RecordingArbiter:
    def __init__(self) -> None:
        self.advance_time_calls: list[int] = []

    def next_boundary_ms(self):
        return None

    def advance_time(self, elapsed_ms: int):
        self.advance_time_calls.append(elapsed_ms)
        return []

    def consume_completed_rest_piece_ids(self):
        return ()


class _FalseyArbiter(RealTimeArbiter):
    """Expose whether a falsey injected scheduling service is actually used."""

    def __bool__(self) -> bool:
        return False

    def is_piece_busy(self, piece_id: str) -> bool:
        return True


class TestMoveRequests:
    """Verify move requests, rejection, and scheduling delegation."""

    def test_legal_move_returns_ok(self) -> None:
        engine, _ = _engine([". . .", ". wR .", ". . ."])

        result = engine.request_move(
            Position(1, 1),
            Position(1, 2),
        )

        assert result.ok
        assert result.reason == "ok"

    def test_uses_falsey_injected_rule_engine(self) -> None:
        board = parse_board(["wR ."])
        engine = GameEngine(
            board,
            rule_engine=_FalseyRuleEngine(),
            arbiter=RealTimeArbiter(),
        )

        result = engine.request_move(Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "injected_rule_engine"

    def test_uses_falsey_injected_arbiter(self) -> None:
        board = parse_board(["wR ."])
        engine = GameEngine(
            board,
            rule_engine=RuleEngine(),
            arbiter=_FalseyArbiter(),
        )

        result = engine.request_move(Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "piece_busy"

    def test_empty_source_reason_propagates_without_starting_motion(self) -> None:
        engine, _ = _engine([". ."])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "empty_source"
        assert engine.snapshot() == before
        assert engine.consume_events() == ()

    def test_friendly_destination_reason_propagates_without_starting_motion(
        self,
    ) -> None:
        engine, _ = _engine(["wR wP"])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "friendly_destination"
        assert engine.snapshot() == before
        assert engine.consume_events() == ()

    def test_illegal_piece_move_reason_propagates_without_starting_motion(
        self,
    ) -> None:
        engine, _ = _engine([". . .", ". wR .", ". . ."])
        before = engine.snapshot()

        result = engine.request_move(
            Position(1, 1),
            Position(0, 2),
        )

        assert not result.ok
        assert result.reason == "illegal_piece_move"
        assert engine.snapshot() == before
        assert engine.consume_events() == ()

    def test_outside_board_reason_propagates_without_starting_motion(self) -> None:
        engine, _ = _engine(["wR ."])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(-1, 0))

        assert not result.ok
        assert result.reason == "outside_board"
        assert engine.snapshot() == before
        assert engine.consume_events() == ()

    def test_game_over_checked_before_rule_engine(self) -> None:
        board = parse_board([". wR ."])
        engine = GameEngine(
            board,
            _FailingMoveRules(),
            RealTimeArbiter(),
        )
        engine._game_over = True

        result = engine.request_move(
            Position(0, 1),
            Position(0, 2),
        )

        assert result.reason == "game_over"

    def test_busy_piece_rejects_second_move(self) -> None:
        engine, _ = _engine([". wR . . ."])
        engine.request_move(
            Position(0, 1),
            Position(0, 4),
        )

        result = engine.request_move(
            Position(0, 1),
            Position(0, 0),
        )

        assert not result.ok
        assert result.reason == "piece_busy"

    def test_wait_delegates_to_arbiter(self) -> None:
        arbiter = _RecordingArbiter()
        board = parse_board([". wR ."])
        engine = GameEngine(
            board,
            RuleEngine(),
            arbiter,
        )

        engine.wait(500)

        assert arbiter.advance_time_calls == [500]


class TestMoveCompletion:
    """Verify completed moves update board and capture state."""

    def test_arrival_moves_piece_on_board(self) -> None:
        engine, board = _engine([". wR . ."])
        source = Position(0, 1)
        destination = Position(0, 3)
        piece = board.get_piece(source)
        engine.request_move(
            source,
            destination,
        )

        engine.wait(2000)

        assert piece is not None
        assert board.get_piece(source) is None
        assert board.get_piece(destination) is piece
        assert piece.cell == destination
        snapshot_piece = next(p for p in engine.snapshot().pieces if p.id == piece.id)
        assert snapshot_piece.cell == destination

    def test_captured_piece_keeps_captured_state(self) -> None:
        engine, board = _engine(["wR . bK"])
        source = Position(0, 0)
        destination = Position(0, 2)
        moving_piece = board.get_piece(source)
        captured_piece = board.get_piece(destination)

        engine.request_move(
            source,
            destination,
        )
        engine.wait(2000)

        assert moving_piece is not None
        assert captured_piece is not None
        assert board.get_piece(source) is None
        assert board.get_piece(destination) is moving_piece
        assert moving_piece.cell == destination
        assert captured_piece.state == "captured"
        assert captured_piece.cell == destination
        snapshot_piece = next(
            piece for piece in engine.snapshot().pieces if piece.id == moving_piece.id
        )
        assert snapshot_piece.cell == destination

    def test_intermediate_step_emits_no_completion_and_starts_no_rest(self) -> None:
        engine, board = _engine(["wR . . ."])
        piece = board.get_piece(Position(0, 0))
        engine.request_move(Position(0, 0), Position(0, 3))
        engine.consume_events()

        engine.wait(1000)

        assert board.get_piece(Position(0, 1)) is piece
        assert piece.state == "moving"
        assert engine.consume_events() == ()
        assert engine.snapshot().rests == ()

    def test_large_wait_crosses_all_cell_boundaries_in_order(self) -> None:
        engine, board = _engine(["wR . . . ."])
        piece = board.get_piece(Position(0, 0))
        engine.request_move(Position(0, 0), Position(0, 4))
        engine.consume_events()

        engine.wait(4000)

        assert board.get_piece(Position(0, 4)) is piece
        assert engine.consume_events() == (
            MoveCompleted(
                piece_id=piece.id,
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 4),
            ),
            RestStarted(
                piece_id=piece.id,
                rest_kind="long_rest",
                duration_ms=10000,
            ),
        )

    def test_knight_ignores_friendly_pieces_on_visual_waypoints(self) -> None:
        engine, board = _engine(
            [
                "wN .",
                "wP .",
                "wP .",
            ]
        )
        knight = board.get_piece(Position(0, 0))
        first_blocker = board.get_piece(Position(1, 0))
        second_blocker = board.get_piece(Position(2, 0))
        engine.request_move(Position(0, 0), Position(2, 1))
        engine.consume_events()

        engine.wait(1000)
        first_transit = engine.snapshot()

        assert board.get_piece(Position(0, 0)) is knight
        assert board.get_piece(Position(1, 0)) is first_blocker
        assert first_transit.motions[0].source == Position(0, 0)
        assert first_transit.motions[0].destination == Position(2, 1)
        assert first_transit.motions[0].elapsed_ms == 1000
        assert first_transit.motions[0].duration_ms == 3000
        assert engine.consume_events() == ()
        assert first_transit.rests == ()

        engine.wait(1000)
        second_transit = engine.snapshot()

        assert board.get_piece(Position(0, 0)) is knight
        assert board.get_piece(Position(2, 0)) is second_blocker
        assert second_transit.motions[0].source == Position(0, 0)
        assert second_transit.motions[0].destination == Position(2, 1)
        assert second_transit.motions[0].elapsed_ms == 2000
        assert second_transit.motions[0].duration_ms == 3000
        assert second_transit.motions[0].action_elapsed_ms == 2000
        assert engine.consume_events() == ()

        engine.wait(999)
        assert board.get_piece(Position(0, 0)) is knight
        assert engine.consume_events() == ()

        engine.wait(1)

        assert board.get_piece(Position(0, 0)) is None
        assert board.get_piece(Position(2, 1)) is knight
        assert knight.state == "long_rest"

    def test_knight_does_not_capture_enemies_on_visual_waypoints(self) -> None:
        engine, board = _engine(
            [
                "wN .",
                "bP .",
                "bP .",
            ]
        )
        knight = board.get_piece(Position(0, 0))
        first_enemy = board.get_piece(Position(1, 0))
        second_enemy = board.get_piece(Position(2, 0))
        engine.request_move(Position(0, 0), Position(2, 1))
        engine.consume_events()

        engine.wait(3000)
        events = engine.consume_events()

        assert board.get_piece(Position(1, 0)) is first_enemy
        assert board.get_piece(Position(2, 0)) is second_enemy
        assert board.get_piece(Position(2, 1)) is knight
        assert first_enemy.state != "captured"
        assert second_enemy.state != "captured"
        assert not any(isinstance(event, PieceCaptured) for event in events)
