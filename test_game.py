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


class BoardPixelTests(unittest.TestCase):
    def setUp(self):
        self.board = Board()
        self.board.load(["wK . .", ". bK ."])

    def test_pixel_inside_board(self):
        self.assertEqual(self.board.pixel_to_cell(50, 50), (0, 0))
        self.assertEqual(self.board.pixel_to_cell(150, 50), (0, 1))
        self.assertEqual(self.board.pixel_to_cell(50, 150), (1, 0))

    def test_pixel_outside_board(self):
        self.assertIsNone(self.board.pixel_to_cell(350, 50))
        self.assertIsNone(self.board.pixel_to_cell(50, 250))

    def test_negative_coordinates(self):
        self.assertIsNone(self.board.pixel_to_cell(-1, 50))
        self.assertIsNone(self.board.pixel_to_cell(50, -1))

    def test_empty_board(self):
        board = Board()
        self.assertIsNone(board.pixel_to_cell(50, 50))


class GameClickTests(unittest.TestCase):
    def _make_game(self, board_lines, commands):
        board_text = "\n".join(board_lines)
        commands_text = "\n".join(commands)
        game = Game()
        game.load(f"Board:\n{board_text}\nCommands:\n{commands_text}\n")
        return game

    def _run_output(self, game):
        output = io.StringIO()
        with redirect_stdout(output):
            game.run()
        return output.getvalue()

    def test_click_moves_piece(self):
        game = self._make_game(["wK ."], ["click 50 50", "click 150 50", "print board"])
        self.assertEqual(self._run_output(game), ". wK\n")

    def test_click_enemy_piece_moves_selected_piece(self):
        game = self._make_game(
            ["wK bR"], ["click 50 50", "click 150 50", "print board"]
        )
        self.assertEqual(self._run_output(game), ". wK\n")

    def test_click_friendly_piece_replaces_selection(self):
        game = self._make_game(
            ["wK wQ ."], ["click 50 50", "click 150 50", "click 250 50", "print board"]
        )
        self.assertEqual(self._run_output(game), "wK . wQ\n")

    def test_click_outside_board_ignored(self):
        game = self._make_game(
            ["wK ."], ["click 50 50", "click 9999 9999", "print board"]
        )
        self.assertEqual(self._run_output(game), "wK .\n")


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
