# pyright: reportOptionalMemberAccess=false

from __future__ import annotations

import pytest

from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position
from kungfu_chess.rules.rule_engine import RuleEngine


class AccessRecordingBoard(Board):
    def __init__(self, width: int, height: int) -> None:
        super().__init__(width, height)
        self.inspected_positions: list[Position] = []

    def get_piece(self, pos: Position) -> Piece | None:
        self.inspected_positions.append(pos)
        return super().get_piece(pos)


@pytest.fixture
def rules() -> RuleEngine:
    return RuleEngine()


class TestRuleEngineBoundary:
    """Verify RuleEngine's own boundary and orchestration responsibilities."""

    @pytest.mark.parametrize("source", [Position(-1, 0), Position(1, 0)])
    def test_outside_source_returns_outside_board_before_piece_inspection(
        self,
        rules: RuleEngine,
        source: Position,
    ) -> None:
        board = AccessRecordingBoard(width=2, height=1)
        destination = Position(0, 1)

        result = rules.validate_move(board, source, destination)

        assert not result.ok
        assert result.reason == "outside_board"
        assert board.inspected_positions == []

    @pytest.mark.parametrize("destination", [Position(0, -1), Position(0, 2)])
    def test_outside_destination_returns_outside_board_before_piece_inspection(
        self,
        rules: RuleEngine,
        destination: Position,
    ) -> None:
        board = AccessRecordingBoard(width=2, height=1)
        source = Position(0, 0)

        result = rules.validate_move(board, source, destination)

        assert not result.ok
        assert result.reason == "outside_board"
        assert board.inspected_positions == []

    def test_empty_source_returns_empty_source(self, rules: RuleEngine) -> None:
        board = parse_board([". ."])

        result = rules.validate_move(board, Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "empty_source"

    def test_friendly_destination_returns_friendly_destination(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board(["wR wP"])

        result = rules.validate_move(board, Position(0, 0), Position(0, 1))

        assert not result.ok
        assert result.reason == "friendly_destination"

    def test_same_source_and_destination_returns_friendly_destination(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board(["wR ."])

        result = rules.validate_move(board, Position(0, 0), Position(0, 0))

        assert not result.ok
        assert result.reason == "friendly_destination"

    def test_invalid_geometry_returns_illegal_piece_move(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board([". . .", ". wR .", ". . ."])

        result = rules.validate_move(board, Position(1, 1), Position(0, 2))

        assert not result.ok
        assert result.reason == "illegal_piece_move"

    def test_blocked_sliding_move_returns_illegal_piece_move(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board(["wR wP ."])

        result = rules.validate_move(board, Position(0, 0), Position(0, 2))

        assert not result.ok
        assert result.reason == "illegal_piece_move"

    def test_legal_destination_returns_ok(self, rules: RuleEngine) -> None:
        board = parse_board([". . .", ". wR .", ". . ."])

        result = rules.validate_move(board, Position(1, 1), Position(1, 2))

        assert result.ok
        assert result.reason == "ok"

    def test_legal_destinations_returns_empty_set_when_no_source_piece(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board([". ."])

        destinations = rules.legal_destinations(board, Position(0, 0))

        assert destinations == set()

    def test_delegates_to_the_matching_piece_rule(self) -> None:
        """RuleEngine should look up and call the piece_rules rule, not reimplement movement."""
        board = parse_board([". . .", ". wR .", ". . ."])
        source = Position(1, 1)
        piece = board.get_piece(source)
        expected_destinations = {Position(9, 9)}
        resolver_calls: list[str] = []
        rule_calls: list[tuple[Board, Position]] = []

        def fake_rule(rule_board: Board, rule_source: Position) -> set[Position]:
            rule_calls.append((rule_board, rule_source))
            return expected_destinations

        def fake_destination_rule_for(kind: str):
            resolver_calls.append(kind)
            return fake_rule

        rules = RuleEngine(destination_rule_resolver=fake_destination_rule_for)
        destinations = rules.legal_destinations(board, source)

        assert piece is not None
        assert resolver_calls == [piece.kind]
        assert rule_calls == [(board, source)]
        assert destinations == expected_destinations

    def test_rule_queries_do_not_mutate_board_or_piece_state(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board(
            [
                "wR . bK",
                ". wP .",
                ". . .",
            ]
        )
        positions = tuple(
            Position(row, col)
            for row in range(board.height)
            for col in range(board.width)
        )
        occupancy_before = tuple(board.get_piece(position) for position in positions)
        pieces_before = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )

        rules.legal_destinations(board, Position(0, 0))
        rules.validate_move(board, Position(1, 1), Position(0, 1))

        occupancy_after = tuple(board.get_piece(position) for position in positions)
        pieces_after = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )
        assert occupancy_after == occupancy_before
        assert pieces_after == pieces_before


class TestRuleEngineJumpValidation:
    """Verify RuleEngine's jump-legality boundary: only piece presence matters."""

    def test_empty_position_returns_no_piece_at_position(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board([". ."])

        result = rules.validate_jump(board, Position(0, 0))

        assert not result.ok
        assert result.reason == "no_piece_at_position"

    def test_occupied_position_returns_ok(self, rules: RuleEngine) -> None:
        board = parse_board(["wR ."])

        result = rules.validate_jump(board, Position(0, 0))

        assert result.ok
        assert result.reason == "ok"

    def test_jump_validation_does_not_mutate_board_or_piece(
        self,
        rules: RuleEngine,
    ) -> None:
        board = parse_board(["wR . bK"])
        before = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )

        rules.validate_jump(board, Position(0, 0))
        rules.validate_jump(board, Position(0, 1))

        after = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )
        assert after == before

    @pytest.mark.parametrize("kind", ["K", "Q", "R", "B", "N", "P"])
    @pytest.mark.parametrize("color", ["w", "b"])
    def test_jump_validation_accepts_every_color_and_kind(
        self,
        rules: RuleEngine,
        kind: str,
        color: str,
    ) -> None:
        """No color- or kind-specific restrictions are applied to jumps."""
        board = parse_board([f"{color}{kind}"])

        result = rules.validate_jump(board, Position(0, 0))

        assert result.ok
        assert result.reason == "ok"
