import unittest
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.io.board_printer import print_board


class TestBoardPrinter(unittest.TestCase):
    def test_round_trip(self):
        lines = ['wR . wK',
                 '. bP .',
                 'bR . bK']
        board = parse_board(lines)
        self.assertEqual(print_board(board), '\n'.join(lines))

    def test_empty_board(self):
        lines = ['. . .', '. . .']
        board = parse_board(lines)
        self.assertEqual(print_board(board), '\n'.join(lines))
