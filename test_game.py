import io
import unittest

from contextlib import redirect_stdout

from game import Piece
from game import Board
from game import Game


class PieceMoveTests(unittest.TestCase):
    def test_king_valid_moves(self):
        king = Piece("wK")
        self.assertTrue(king.can_move_to(4, 4, 5, 4))
        self.assertTrue(king.can_move_to(4, 4, 4, 5))
        self.assertTrue(king.can_move_to(4, 4, 5, 5))
        self.assertTrue(king.can_move_to(4, 4, 3, 3))

    def test_king_invalid_moves(self):
        king = Piece("wK")
        self.assertFalse(king.can_move_to(4, 4, 6, 4))
        self.assertFalse(king.can_move_to(4, 4, 4, 4))

    def test_rook_valid_moves(self):
        rook = Piece("wR")
        self.assertTrue(rook.can_move_to(0, 0, 0, 5))
        self.assertTrue(rook.can_move_to(0, 0, 5, 0))

    def test_rook_invalid_moves(self):
        rook = Piece("wR")
        self.assertFalse(rook.can_move_to(0, 0, 3, 3))

    def test_bishop_valid_moves(self):
        bishop = Piece("wB")
        self.assertTrue(bishop.can_move_to(0, 0, 3, 3))
        self.assertTrue(bishop.can_move_to(4, 4, 1, 1))

    def test_bishop_invalid_moves(self):
        bishop = Piece("wB")
        self.assertFalse(bishop.can_move_to(0, 0, 0, 3))
        self.assertFalse(bishop.can_move_to(0, 0, 3, 2))

    def test_queen_valid_moves(self):
        queen = Piece("wQ")
        self.assertTrue(queen.can_move_to(4, 4, 4, 7))
        self.assertTrue(queen.can_move_to(4, 4, 7, 4))
        self.assertTrue(queen.can_move_to(4, 4, 7, 7))

    def test_queen_invalid_moves(self):
        queen = Piece("wQ")
        self.assertFalse(queen.can_move_to(4, 4, 6, 5))

    def test_knight_valid_moves(self):
        knight = Piece("wN")
        self.assertTrue(knight.can_move_to(4, 4, 6, 5))
        self.assertTrue(knight.can_move_to(4, 4, 2, 3))
        self.assertTrue(knight.can_move_to(4, 4, 5, 6))

    def test_knight_invalid_moves(self):
        knight = Piece("wN")
        self.assertFalse(knight.can_move_to(4, 4, 4, 6))
        self.assertFalse(knight.can_move_to(4, 4, 6, 6))

    def test_empty_piece_cannot_move(self):
        empty = Piece(".")
        self.assertFalse(empty.can_move_to(0, 0, 1, 1))

    def test_no_piece_can_move_to_same_cell(self):
        for token in ["wR", "wB", "wQ", "wK", "wN"]:
            piece = Piece(token)
            self.assertFalse(
                piece.can_move_to(4, 4, 4, 4),
                msg=f"{token} should not move to same cell",
            )

    def test_pawn_has_no_movement_in_iteration_3(self):
        pawn = Piece("wP")
        self.assertFalse(pawn.can_move_to(4, 4, 3, 4))
        self.assertFalse(pawn.can_move_to(4, 4, 3, 3))


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


class BoardPathTests(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_horizontal_path_clear(self):
        self.board.load(["wR . . ."])
        self.assertTrue(self.board.is_path_clear(0, 0, 0, 3))

    def test_horizontal_path_blocked(self):
        self.board.load(["wR . bP ."])
        self.assertFalse(self.board.is_path_clear(0, 0, 0, 3))

    def test_vertical_path_blocked(self):
        self.board.load(["wR", ".", "bP", "."])
        self.assertFalse(self.board.is_path_clear(0, 0, 3, 0))

    def test_diagonal_path_clear(self):
        self.board.load(["wB . .", ". . .", ". . ."])
        self.assertTrue(self.board.is_path_clear(0, 0, 2, 2))

    def test_diagonal_path_blocked(self):
        self.board.load(["wB . .", ". bP .", ". . ."])
        self.assertFalse(self.board.is_path_clear(0, 0, 2, 2))

    def test_adjacent_cells_path_clear(self):
        self.board.load(["wR bR"])
        self.assertTrue(self.board.is_path_clear(0, 0, 0, 1))

    def test_can_move_piece_rejects_friendly_destination(self):
        self.board.load(["wR . wB"])
        self.assertFalse(self.board.can_move_piece(0, 0, 0, 2))

    def test_can_move_piece_rejects_empty_source(self):
        self.board.load([". . wB"])
        self.assertFalse(self.board.can_move_piece(0, 0, 0, 2))

    def test_can_move_piece_accepts_enemy_destination(self):
        self.board.load(["wR . bB"])
        self.assertTrue(self.board.can_move_piece(0, 0, 0, 2))


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

    def test_invalid_move_is_ignored(self):
        game = self._make_game(
            ["wK . . ."], ["click 50 50", "click 350 50", "print board"]
        )
        self.assertEqual(self._run_output(game), "wK . . .\n")

    def test_move_to_same_cell_is_ignored(self):
        game = self._make_game(["wK ."], ["click 50 50", "click 50 50", "print board"])
        self.assertEqual(self._run_output(game), "wK .\n")

    def test_selection_preserved_after_illegal_move(self):
        game = self._make_game(
            ["wK . . ."], ["click 50 50", "click 350 50", "click 150 50", "print board"]
        )
        self.assertEqual(self._run_output(game), ". wK . .\n")

    def test_click_enemy_piece_on_legal_destination_moves_selected_piece(self):
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

    def test_rook_legal_move_via_click(self):
        game = self._make_game(
            ["wR . . ."], ["click 50 50", "click 350 50", "print board"]
        )
        self.assertEqual(self._run_output(game), ". . . wR\n")

    def test_rook_blocked_via_click_is_ignored(self):
        game = self._make_game(
            ["wR . bP ."], ["click 50 50", "click 350 50", "print board"]
        )
        self.assertEqual(self._run_output(game), "wR . bP .\n")

    def test_rook_diagonal_move_ignored_via_click(self):
        game = self._make_game(
            ["wR . . .", ". . . ."], ["click 50 50", "click 150 150", "print board"]
        )
        self.assertEqual(self._run_output(game), "wR . . .\n. . . .\n")

    def test_bishop_blocked_via_click_is_ignored(self):
        game = self._make_game(
            ["wB . .", ". bP .", ". . ."],
            ["click 50 50", "click 250 250", "print board"],
        )
        self.assertEqual(self._run_output(game), "wB . .\n. bP .\n. . .\n")

    def test_knight_jumps_over_blocker_via_click(self):
        game = self._make_game(
            ["wN wP .", ". . .", ". . ."],
            ["click 50 50", "click 150 250", "print board"],
        )
        self.assertEqual(self._run_output(game), ". wP .\n. . .\n. wN .\n")

    def test_queen_blocked_via_click_is_ignored(self):
        game = self._make_game(
            ["wQ . bP ."], ["click 50 50", "click 350 50", "print board"]
        )
        self.assertEqual(self._run_output(game), "wQ . bP .\n")

    def test_enemy_capture_via_click(self):
        game = self._make_game(
            ["wR . bB"], ["click 50 50", "click 250 50", "print board"]
        )
        self.assertEqual(self._run_output(game), ". . wR\n")

    def test_friendly_piece_click_replaces_selection_not_capture(self):
        game = self._make_game(
            ["wR . wQ"], ["click 50 50", "click 250 50", "click 150 50", "print board"]
        )
        self.assertEqual(self._run_output(game), "wR wQ .\n")

    def test_knight_legal_move_via_click(self):
        game = self._make_game(
            ["wN . .", ". . .", ". . ."],
            ["click 50 50", "click 150 250", "print board"],
        )
        self.assertEqual(self._run_output(game), ". . .\n. . .\n. wN .\n")


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
