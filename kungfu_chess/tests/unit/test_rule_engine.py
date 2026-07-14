from __future__ import annotations

import unittest
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.position import Position


class TestRuleEngineBoundary(unittest.TestCase):
    """Verify RuleEngine's own boundary and orchestration responsibilities."""

    def setUp(self) -> None:
        self.rules = RuleEngine()

    def test_missing_source_returns_explicit_validation_reason(self) -> None:
        board = parse_board([". ."])

        result = self.rules.validate_move(board, Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_piece_at_source")

    def test_illegal_destination_returns_illegal_move(self) -> None:
        board = parse_board([". . .", ". wR .", ". . ."])

        result = self.rules.validate_move(board, Position(1, 1), Position(0, 2))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "illegal_move")

    def test_legal_destination_returns_ok(self) -> None:
        board = parse_board([". . .", ". wR .", ". . ."])

        result = self.rules.validate_move(board, Position(1, 1), Position(1, 2))

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "ok")

    def test_legal_destinations_returns_empty_set_when_no_source_piece(self) -> None:
        board = parse_board([". ."])

        destinations = self.rules.legal_destinations(board, Position(0, 0))

        self.assertEqual(destinations, set())

    def test_delegates_to_the_matching_piece_rule(self) -> None:
        """RuleEngine should defer to piece_rules rather than reimplement movement."""
        board = parse_board(
            [
                ". . . . .",
                ". wP wP wP .",
                ". wP wN wP .",
                ". wP wP wP .",
                ". . . . .",
            ]
        )

        destinations = self.rules.legal_destinations(board, Position(2, 2))

        self.assertIn(Position(0, 1), destinations)
        self.assertIn(Position(4, 3), destinations)

    def test_rule_queries_do_not_mutate_board_or_piece_state(self) -> None:
        board = parse_board(
            [
                "wR . bK",
                ". wP .",
                ". . .",
            ]
        )
        before = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )

        self.rules.legal_destinations(board, Position(0, 0))
        self.rules.validate_move(board, Position(1, 1), Position(0, 1))

        after = tuple(
            (piece.id, piece.cell, piece.kind, piece.state)
            for piece in board.all_pieces()
        )
        self.assertEqual(after, before)
