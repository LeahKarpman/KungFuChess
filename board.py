from piece import EMPTY_TOKEN, Piece

CELL_SIZE = 100

SLIDING_KINDS = {"R", "B", "Q"}


class Board:
    def __init__(self):
        self._rows = []

    def load(self, board_lines):
        self._rows = []
        expected_width = None

        for line in board_lines:
            tokens = line.split()

            if expected_width is None:
                expected_width = len(tokens)
            elif len(tokens) != expected_width:
                raise ValueError("ROW_WIDTH_MISMATCH")

            row = []
            for token in tokens:
                if not Piece.is_valid_token(token):
                    raise ValueError("UNKNOWN_TOKEN")
                row.append(Piece(token))

            self._rows.append(row)

    def pixel_to_cell(self, x, y):
        if not self._rows:
            return None
        if x < 0 or y < 0:
            return None
        row = y // CELL_SIZE
        col = x // CELL_SIZE
        if row >= len(self._rows) or col >= len(self._rows[0]):
            return None
        return (row, col)

    def is_path_clear(self, from_row, from_col, to_row, to_col):
        dr = to_row - from_row
        dc = to_col - from_col
        if dr != 0 and dc != 0 and abs(dr) != abs(dc):
            return False
        row_step = 0 if dr == 0 else dr // abs(dr)
        col_step = 0 if dc == 0 else dc // abs(dc)
        row = from_row + row_step
        col = from_col + col_step
        while (row, col) != (to_row, to_col):
            if not self._rows[row][col].is_empty:
                return False
            row += row_step
            col += col_step
        return True

    def can_move_piece(self, from_row, from_col, to_row, to_col):
        source = self._rows[from_row][from_col]
        destination = self._rows[to_row][to_col]
        if source.is_empty:
            return False
        if not source.can_move_to(from_row, from_col, to_row, to_col):
            return False
        if not destination.is_empty and destination.color == source.color:
            return False
        if source.kind in SLIDING_KINDS and not self.is_path_clear(
            from_row, from_col, to_row, to_col
        ):
            return False
        return True

    def get_piece(self, row, col):
        return self._rows[row][col]

    def move_piece(self, from_row, from_col, to_row, to_col):
        piece = self._rows[from_row][from_col]
        self._rows[to_row][to_col] = piece
        self._rows[from_row][from_col] = Piece(EMPTY_TOKEN)

    def print_board(self):
        for row in self._rows:
            print(" ".join(piece.token for piece in row))
