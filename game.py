EMPTY_TOKEN = "."

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

    def print_board(self):

        for row in self._rows:
            print(" ".join(piece.token for piece in row))


class Game:
    def __init__(self):
        self._board = Board()
        self._commands = []

    def load(self, text):

        self._board = Board()
        self._commands = []

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

    def run(self):

        for command in self._commands:
            if command == "print board":
                self._board.print_board()
