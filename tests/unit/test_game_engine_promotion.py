import unittest

from kungfu_chess.model.position import Position
from tests.unit.game_engine_test_support import make_engine as _engine


class TestPromotion(unittest.TestCase):
    """Verify that pawn promotion is applied only when a move arrives."""

    def test_white_pawn_promotes_to_queen_on_top_row(self) -> None:
        engine, board = _engine([".", "wP"])

        result = engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(0, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(promoted)
        self.assertEqual(promoted.kind, "Q")
        self.assertEqual(engine.snapshot().pieces[0].kind, "Q")

    def test_black_pawn_promotes_to_queen_on_bottom_row(self) -> None:
        engine, board = _engine(["bP", "."])

        result = engine.request_move(Position(0, 0), Position(1, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(1, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(promoted)
        self.assertEqual(promoted.kind, "Q")

    def test_pawn_is_not_promoted_before_arrival(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn = board.get_piece(Position(1, 0))

        result = engine.request_move(Position(1, 0), Position(0, 0))

        self.assertTrue(result.ok)
        self.assertIs(board.get_piece(Position(1, 0)), pawn)
        self.assertEqual(pawn.kind, "P")
        self.assertEqual(engine.snapshot().pieces[0].kind, "P")

    def test_non_pawn_keeps_its_kind_on_last_row(self) -> None:
        engine, board = _engine([".", "wR"])

        result = engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        rook = board.get_piece(Position(0, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(rook)
        self.assertEqual(rook.kind, "R")


class TestCooldownPromotion(unittest.TestCase):
    def test_promoted_pawn_retains_its_identity(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn_id = board.get_piece(Position(1, 0)).id

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 0)).id, pawn_id)

    def test_promoted_piece_enters_long_rest_after_move(self) -> None:
        engine, board = _engine([".", "wP"])

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(0, 0))
        self.assertEqual(promoted.kind, "Q")
        self.assertEqual(promoted.state, "long_rest")

    def test_rest_snapshot_references_the_promoted_piece(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn_id = board.get_piece(Position(1, 0)).id

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        rests = engine.snapshot().rests
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].piece_id, pawn_id)
