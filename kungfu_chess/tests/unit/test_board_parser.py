import unittest
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.position import Position


class TestBoardParser(unittest.TestCase):
    def test_valid_board(self):
        lines = ['wR wN wB wQ wK wB wN wR',
                 'wP wP wP wP wP wP wP wP',
                 '. . . . . . . .',
                 '. . . . . . . .',
                 '. . . . . . . .',
                 '. . . . . . . .',
                 'bP bP bP bP bP bP bP bP',
                 'bR bN bB bQ bK bB bN bR']
        board = parse_board(lines)
        self.assertEqual(board.width, 8)
        self.assertEqual(board.height, 8)
        piece = board.get_piece(Position(0, 0))
        self.assertEqual(piece.color, 'w')
        self.assertEqual(piece.kind, 'R')

    def test_empty_cell(self):
        board = parse_board(['. .', '. .'])
        self.assertIsNone(board.get_piece(Position(0, 0)))

    def test_inconsistent_row_raises(self):
        with self.assertRaises(ValueError):
            parse_board(['wK wQ', 'bK'])

    def test_invalid_token_raises(self):
        with self.assertRaises(ValueError):
            parse_board(['wK xZ'])

    def test_piece_id_format(self):
        board = parse_board(['wK .'])
        piece = board.get_piece(Position(0, 0))
        self.assertEqual(piece.id, 'wK_0_0')
