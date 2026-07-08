import io
import unittest

from contextlib import redirect_stdout

from game import Piece
from game import Board
from game import Game


class PieceTests(unittest.TestCase):
    def test_empty_piece(self):

        piece = Piece(".")

        self.assertTrue(piece.is_empty)
        self.assertIsNone(piece.color)
        self.assertIsNone(piece.kind)

    def test_white_king(self):

        piece = Piece("wK")

        self.assertFalse(piece.is_empty)
        self.assertEqual(piece.color, "w")
        self.assertEqual(piece.kind, "K")

    def test_black_rook(self):

        piece = Piece("bR")

        self.assertEqual(piece.color, "b")
        self.assertEqual(piece.kind, "R")

    def test_invalid_token(self):

        self.assertFalse(Piece.is_valid_token("abc"))
        self.assertFalse(Piece.is_valid_token("xK"))
        self.assertFalse(Piece.is_valid_token("wX"))

    def test_valid_token(self):

        self.assertTrue(Piece.is_valid_token("wQ"))
        self.assertTrue(Piece.is_valid_token("bP"))
        self.assertTrue(Piece.is_valid_token("."))


class BoardTests(unittest.TestCase):
    def test_load_board(self):

        board = Board()

        board.load(["wK .", ". bK"])

    def test_row_width_mismatch(self):

        board = Board()

        with self.assertRaises(ValueError):
            board.load(["wK . .", ". bK"])

    def test_unknown_token(self):

        board = Board()

        with self.assertRaises(ValueError):
            board.load(["wK xZ"])


class BoardPrintTests(unittest.TestCase):
    def test_print_board(self):

        board = Board()
        board.load(["wK .", ". bK"])

        output = io.StringIO()

        with redirect_stdout(output):
            board.print_board()

        self.assertEqual(output.getvalue(), "wK .\n. bK\n")

    def test_load_is_idempotent(self):

        board = Board()
        board.load(["wK .", ". bK"])
        board.load(["bR"])

        output = io.StringIO()

        with redirect_stdout(output):
            board.print_board()

        self.assertEqual(output.getvalue(), "bR\n")


class GameTests(unittest.TestCase):
    def test_print_board(self):

        text = """Board:
wK .
. bK
Commands:
print board
"""

        game = Game()

        game.load(text)

        output = io.StringIO()

        with redirect_stdout(output):
            game.run()

        self.assertEqual(output.getvalue(), "wK .\n. bK\n")

    def test_load_is_idempotent(self):

        first = """Board:
wK .
. bK
Commands:
print board
"""
        second = """Board:
bR
Commands:
print board
"""

        game = Game()
        game.load(first)
        game.load(second)

        output = io.StringIO()

        with redirect_stdout(output):
            game.run()

        self.assertEqual(output.getvalue(), "bR\n")

    def test_unknown_token_raises_via_game_load(self):

        text = """Board:
wK xZ
Commands:
"""

        game = Game()

        with self.assertRaises(ValueError):
            game.load(text)


if __name__ == "__main__":
    unittest.main()
