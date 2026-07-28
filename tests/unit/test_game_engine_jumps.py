# pyright: reportOptionalMemberAccess=false

import pytest

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.events import JumpStarted
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import JumpValidation, RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class _RecordingJumpRules:
    def __init__(self, result: JumpValidation | None = None) -> None:
        self.result = result
        self.calls: list[tuple[object, Position]] = []

    def validate_jump(self, board, pos: Position) -> JumpValidation:
        self.calls.append((board, pos))
        if self.result is None:
            raise AssertionError("validate_jump must not be called")
        return self.result


class TestLandingReservation:
    """Verify landing-cell behavior during a jump."""

    def test_enemy_may_move_to_landing_cell(self) -> None:
        lines = [". . .", "wP bR .", ". . ."]
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))

        result = engine.request_move(
            Position(1, 1),
            Position(1, 0),
        )

        assert result.ok
        assert result.reason == "ok"

    def test_friendly_piece_blocked_from_landing_cell(self) -> None:
        lines = [". . .", "wP . wR", ". . ."]
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))

        result = engine.request_move(
            Position(1, 2),
            Position(1, 0),
        )

        assert not result.ok
        assert result.reason == "landing_reserved"

    def test_enemy_arrives_then_jumper_lands_captures_enemy(
        self,
    ) -> None:
        lines = [". . .", "wP bR .", ". . ."]
        engine, board = _engine(lines)
        landing = Position(1, 0)
        enemy_source = Position(1, 1)
        jumping_piece = board.get_piece(landing)
        captured_piece = board.get_piece(enemy_source)
        engine.jump(landing)
        engine.request_move(
            enemy_source,
            landing,
        )

        engine.wait(1000)

        assert jumping_piece is not None
        assert captured_piece is not None
        assert board.get_piece(landing) is jumping_piece
        assert board.get_piece(enemy_source) is None
        assert jumping_piece.cell == landing
        assert captured_piece.cell == landing
        assert captured_piece.state == "captured"
        snapshot_piece = next(
            piece for piece in engine.snapshot().pieces if piece.id == jumping_piece.id
        )
        assert snapshot_piece.cell == landing

    def test_jump_capture_of_enemy_king_sets_game_over(self) -> None:
        """Apply the king-capture rule through the jump arrival path."""
        engine, board = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        result = engine.request_move(Position(1, 1), Position(1, 0))

        assert result.ok
        engine.wait(1000)

        winner = board.get_piece(Position(1, 0))
        assert winner is not None
        assert winner.color == "w"
        assert engine.game_over


class TestJumpScheduling:
    """Verify that jump timing is delegated to the real-time arbiter."""

    def test_jump_on_empty_cell_leaves_game_unchanged(self) -> None:
        """Ignore a valid board position that does not contain a piece."""
        engine, _ = _engine([". ."])
        before = engine.snapshot()

        engine.jump(Position(0, 0))

        assert engine.snapshot() == before

    def test_jump_after_game_over_leaves_game_unchanged(self) -> None:
        """Reject new jump actions after a king has been captured."""
        engine, _ = _engine(["wR . bK", ". . wP"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        before = engine.snapshot()

        engine.jump(Position(1, 2))

        assert engine.game_over
        assert engine.snapshot() == before

    def test_snapshot_includes_airborne_piece_and_jump_action(self) -> None:
        engine, _ = _engine([". wK ."])
        landing = Position(0, 1)

        engine.jump(landing)
        snapshot = engine.snapshot()

        assert len(snapshot.pieces) == 1
        assert snapshot.pieces[0].id == "wK_0_1"
        assert snapshot.pieces[0].cell == landing
        assert snapshot.pieces[0].state == "moving"
        assert len(snapshot.motions) == 1
        assert snapshot.motions[0].piece_id == "wK_0_1"
        assert snapshot.motions[0].action_kind == "jump"

    def test_jump_marks_piece_busy_in_arbiter(self) -> None:
        board = parse_board([". wK ."])
        arbiter = RealTimeArbiter()
        engine = GameEngine(
            board,
            RuleEngine(),
            arbiter,
        )

        engine.jump(Position(0, 1))

        assert arbiter.is_piece_busy("wK_0_1")

    def test_jump_updates_piece_lifecycle(self) -> None:
        engine, board = _engine([". wK ."])
        landing = Position(0, 1)
        piece = board.get_piece(landing)

        engine.jump(landing)

        assert piece is not None
        assert board.get_piece(landing) is None
        assert piece.cell == landing
        assert piece.state == "moving"

        engine.wait(1000)

        assert board.get_piece(landing) is piece
        assert piece.cell == landing
        assert piece.state == "short_rest"
        snapshot_piece = next(p for p in engine.snapshot().pieces if p.id == piece.id)
        assert snapshot_piece.cell == landing

    def test_game_engine_does_not_store_airborne_pieces(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))

        assert not hasattr(engine, "_airborne")

    def test_black_piece_can_jump(self) -> None:
        engine, board = _engine([". bK ."])

        engine.jump(Position(0, 1))
        engine.wait(1000)

        piece = board.get_piece(Position(0, 1))
        assert piece is not None
        assert piece.color == "b"

    def test_two_pieces_can_jump_concurrently(self) -> None:
        engine, board = _engine(["wK . bK"])

        engine.jump(Position(0, 0))
        engine.jump(Position(0, 2))
        engine.wait(1000)

        first_piece = board.get_piece(Position(0, 0))
        second_piece = board.get_piece(Position(0, 2))

        assert first_piece is not None
        assert second_piece is not None
        assert first_piece.id == "wK_0_0"
        assert second_piece.id == "bK_0_2"

    def test_moving_piece_cannot_start_jump(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )

        engine.jump(Position(0, 0))
        engine.wait(2000)

        arrived_piece = board.get_piece(Position(0, 2))

        assert board.get_piece(Position(0, 0)) is None
        assert arrived_piece is not None
        assert arrived_piece.id == "wR_0_0"


class TestJumpResult:
    """Verify the explicit JumpResult returned by GameEngine.jump()."""

    def test_valid_jump_returns_ok(self) -> None:
        engine, _ = _engine([". wK ."])

        result = engine.jump(Position(0, 1))

        assert result.ok
        assert result.reason == "ok"

    def test_empty_position_returns_no_piece_at_position(self) -> None:
        engine, _ = _engine([". ."])

        result = engine.jump(Position(0, 0))

        assert not result.ok
        assert result.reason == "no_piece_at_position"

    def test_busy_piece_returns_piece_busy(self) -> None:
        """A piece still on the board but scheduled elsewhere cannot also jump."""
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 2))

        result = engine.jump(Position(0, 0))

        assert not result.ok
        assert result.reason == "piece_busy"

    def test_game_over_returns_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        assert engine.game_over

        result = engine.jump(Position(0, 2))

        assert not result.ok
        assert result.reason == "game_over"

    def test_game_over_checked_before_rule_engine(self) -> None:
        rules = _RecordingJumpRules()
        board = parse_board([". wK ."])
        engine = GameEngine(board, rules, RealTimeArbiter())
        engine._game_over = True

        result = engine.jump(Position(0, 1))

        assert result.reason == "game_over"
        assert rules.calls == []

    def test_rejected_jump_does_not_mutate_board(self) -> None:
        engine, board = _engine([". ."])

        engine.jump(Position(0, 0))

        assert board.get_piece(Position(0, 0)) is None

    def test_rejected_jump_emits_no_jump_started(self) -> None:
        engine, _ = _engine([". ."])

        engine.jump(Position(0, 0))

        assert engine.consume_events() == ()

    def test_accepted_jump_starts_through_arbiter(self) -> None:
        board = parse_board([". wK ."])
        arbiter = RealTimeArbiter()
        engine = GameEngine(board, RuleEngine(), arbiter)

        engine.jump(Position(0, 1))

        assert arbiter.is_piece_busy("wK_0_1")

    def test_accepted_jump_emits_exactly_one_jump_started(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))

        events = engine.consume_events()
        jump_started_events = [event for event in events if isinstance(event, JumpStarted)]
        assert len(jump_started_events) == 1

    def test_jump_validation_is_delegated_to_rule_engine(self) -> None:
        rules = _RecordingJumpRules(
            JumpValidation(ok=False, reason="injected_reason")
        )
        board = parse_board([". wK ."])
        engine = GameEngine(board, rules, RealTimeArbiter())

        result = engine.jump(Position(0, 1))

        assert rules.calls == [(board, Position(0, 1))]
        assert not result.ok
        assert result.reason == "injected_reason"

    def test_jump_rejects_gracefully_when_rule_engine_disagrees_with_board(self) -> None:
        """A RuleEngine that (incorrectly) approves a jump with no piece there
        must not crash GameEngine.jump(); it must reject cleanly instead.
        """
        rules = _RecordingJumpRules(JumpValidation(ok=True, reason="ok"))
        board = parse_board([". ."])
        engine = GameEngine(board, rules, RealTimeArbiter())

        result = engine.jump(Position(0, 0))

        assert not result.ok
        assert result.reason == "no_piece_at_position"

    @pytest.mark.parametrize("kind", ["K", "Q", "R", "B", "N", "P"])
    def test_all_piece_kinds_can_request_jump(self, kind: str) -> None:
        engine, _ = _engine([f"w{kind}"])

        result = engine.jump(Position(0, 0))

        assert result.ok

    @pytest.mark.parametrize("color", ["w", "b"])
    def test_both_colors_can_request_jump(self, color: str) -> None:
        engine, _ = _engine([f"{color}K"])

        result = engine.jump(Position(0, 0))

        assert result.ok
