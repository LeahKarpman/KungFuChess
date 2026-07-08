EMPTY_TOKEN = "."

CELL_SIZE = 100

VALID_COLORS = {"w", "b"}

VALID_KINDS = {"K", "Q", "R", "B", "N", "P"}


class Piece:
    def __init__(self, token):
        self._token = token

    @property
    def token(self):
        return self._token

    @property
    def is_empty(self):
        return self._token == EMPTY_TOKEN

    @property
    def color(self):
        if self.is_empty:
            return None
        return self._token[0]

    @property
    def kind(self):
        if self.is_empty:
            return None
        return self._token[1]

    @staticmethod
    def is_valid_token(token):

        if token == EMPTY_TOKEN:
            return True

        if len(token) != 2:
            return False

        return token[0] in VALID_COLORS and token[1] in VALID_KINDS


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

    def get_piece(self, row, col):
        return self._rows[row][col]

    def move_piece(self, from_row, from_col, to_row, to_col):
        piece = self._rows[from_row][from_col]
        self._rows[to_row][to_col] = piece
        self._rows[from_row][from_col] = Piece(EMPTY_TOKEN)

    def print_board(self):

        for row in self._rows:
            print(" ".join(piece.token for piece in row))


class Game:
    def __init__(self):
        self._board = Board()
        self._commands = []
        self._selected = None
        self._clock = 0

    def load(self, text):

        self._board = Board()
        self._commands = []
        self._selected = None
        self._clock = 0

        board_lines = []

        section = None

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            if line == "Board:":
                section = "board"
                continue

            if line == "Commands:":
                section = "commands"
                continue

            if section == "board":
                board_lines.append(line)

            elif section == "commands":
                self._commands.append(line)

        self._board.load(board_lines)

    def _handle_click(self, row, col):

        piece = self._board.get_piece(row, col)

        if self._selected is None:
            if not piece.is_empty:
                self._selected = (row, col)
            return

        selected_piece = self._board.get_piece(*self._selected)

        if not piece.is_empty and piece.color == selected_piece.color:
            self._selected = (row, col)
            return

        self._board.move_piece(*self._selected, row, col)
        self._selected = None

    def run(self):

        for command in self._commands:
            if command == "print board":
                self._board.print_board()

            elif command.startswith("click "):
                parts = command.split()
                x, y = int(parts[1]), int(parts[2])
                cell = self._board.pixel_to_cell(x, y)
                if cell is not None:
                    self._handle_click(*cell)

            elif command.startswith("wait "):
                self._clock += int(command.split()[1])
