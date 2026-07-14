import unittest
from kungfu_chess.engine.game_snapshot import GameSnapshot, PieceSnapshot
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.io.board_printer import print_board, print_snapshot
from kungfu_chess.model.position import Position


class TestBoardPrinter(unittest.TestCase):
    def test_round_trip(self):
        lines = ["wR . wK", ". bP .", "bR . bK"]
        board = parse_board(lines)
        self.assertEqual(print_board(board), "\n".join(lines))

    def test_empty_board(self):
        lines = [". . .", ". . ."]
        board = parse_board(lines)
        self.assertEqual(print_board(board), "\n".join(lines))

    def test_print_snapshot_uses_immutable_piece_views(self) -> None:
        """Render a game snapshot without requiring access to the live board."""
        snapshot = GameSnapshot(
            pieces=(
                PieceSnapshot(
                    id="wK_0_1",
                    color="w",
                    kind="K",
                    cell=Position(0, 1),
                    state="moving",
                ),
            ),
            motions=(),
            selected=None,
            game_over=False,
            width=3,
            height=2,
        )

        self.assertEqual(print_snapshot(snapshot), ". wK .\n. . .")
