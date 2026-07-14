from __future__ import annotations

import unittest
from unittest.mock import Mock, patch
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
        """RuleEngine should look up and call the piece_rules rule, not reimplement movement."""
        board = parse_board([". . .", ". wR .", ". . ."])
        source = Position(1, 1)
        piece = board.get_piece(source)
        expected_destinations = {Position(9, 9)}
        fake_rule = Mock(return_value=expected_destinations)
        fake_destination_rule_for = Mock(return_value=fake_rule)

        with patch(
            "kungfu_chess.rules.rule_engine.destination_rule_for",
            fake_destination_rule_for,
        ):
            destinations = self.rules.legal_destinations(board, source)

        fake_destination_rule_for.assert_called_once_with(piece.kind)
        fake_rule.assert_called_once_with(board, source)
        self.assertEqual(destinations, expected_destinations)

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
