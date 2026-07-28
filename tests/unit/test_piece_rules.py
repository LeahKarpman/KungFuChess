from __future__ import annotations

from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.rules import piece_rules


class TestRookRules:
    """Verify orthogonal sliding and blocker behavior for rooks."""

    def _board(self, lines: list[str]) -> Board:
        return parse_board(lines)

    def test_rook_legal_destinations_empty_board(self):
        board = self._board(
            [
                ". . . . .",
                ". . . . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        src = Position(2, 2)
        dests = piece_rules.rook_destinations(board, src)
        expected = {Position(r, 2) for r in range(5) if r != 2} | {
            Position(2, c) for c in range(5) if c != 2
        }
        assert dests == expected

    def test_rook_blocked_by_friendly(self):
        # A friendly pawn directly above the rook blocks its path.
        board = self._board(
            [
                ". . . . .",
                ". . wP . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        assert Position(1, 2) not in dests  # The friendly square is unavailable.
        assert Position(0, 2) not in dests  # Squares beyond it are unavailable.

    def test_rook_includes_enemy_blocker_and_cannot_move_past_it(self):
        # An enemy pawn directly above the rook blocks its path.
        board = self._board(
            [
                ". . . . .",
                ". . bP . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        assert Position(1, 2) in dests  # The enemy square is capturable.
        assert Position(0, 2) not in dests  # Squares beyond it are unavailable.

    def test_rook_cannot_move_diagonally(self):
        board = self._board(
            [
                ". . . . .",
                ". . . . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        assert Position(1, 1) not in dests
        assert Position(3, 3) not in dests


class TestOtherPieceRules:
    """Verify movement rules that are independent of pawn direction."""

    def test_bishop_moves_diagonally_and_stops_at_enemy(self) -> None:
        board = parse_board(
            [
                "bP . . . .",
                ". . . . .",
                ". . wB . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.bishop_destinations(board, Position(2, 2))

        assert Position(0, 0) in destinations
        assert Position(2, 3) not in destinations

    def test_bishop_cannot_pass_friendly_blocker(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". wP . . .",
                ". . wB . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.bishop_destinations(board, Position(2, 2))

        assert Position(1, 1) not in destinations
        assert Position(0, 0) not in destinations

    def test_queen_combines_rook_and_bishop_destinations(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". . . . .",
                ". . wQ . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.queen_destinations(board, Position(2, 2))

        assert Position(2, 4) in destinations
        assert Position(0, 0) in destinations
        assert Position(0, 1) not in destinations

    def test_king_moves_one_cell_and_cannot_land_on_friendly_piece(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". wK wP",
                ". . .",
            ]
        )

        destinations = piece_rules.king_destinations(board, Position(1, 1))

        assert Position(0, 0) in destinations
        assert Position(1, 2) not in destinations

    def test_knight_jumps_over_adjacent_blockers(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". wP wP wP .",
                ". wP wN wP .",
                ". wP wP wP .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.knight_destinations(board, Position(2, 2))

        assert Position(0, 1) in destinations
        assert Position(4, 3) in destinations

    def test_knight_cannot_land_on_friendly_piece(self) -> None:
        board = parse_board(
            [
                ". wP . . .",
                ". . . . .",
                ". . wN . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.knight_destinations(board, Position(2, 2))

        assert Position(0, 1) not in destinations


class TestPawnRules:
    """Verify direction, double steps, blockers, and pawn captures."""

    def test_white_pawn_moves_up_and_may_double_step_from_start(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". . .",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        assert Position(1, 1) in destinations
        assert Position(0, 1) in destinations

    def test_black_pawn_moves_down_and_may_double_step_from_start(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". bP .",
                ". . .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(1, 1))

        assert Position(2, 1) in destinations
        assert Position(3, 1) in destinations

    def test_pawn_captures_enemy_diagonally(self) -> None:
        board = parse_board(
            [
                ". . .",
                "bR . bN",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        assert Position(1, 0) in destinations
        assert Position(1, 2) in destinations

    def test_pawn_cannot_move_forward_into_occupied_cell(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". bR .",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        assert Position(1, 1) not in destinations
        assert Position(0, 1) not in destinations

    def test_pawn_cannot_double_step_outside_start_row(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". . .",
                ". wP .",
                ". . .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        assert Position(1, 1) in destinations
        assert Position(0, 1) not in destinations
