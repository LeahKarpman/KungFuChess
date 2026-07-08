from board import Board
from piece import Piece

__all__ = ["Game", "Board", "Piece"]


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

        if (row, col) == self._selected:
            return

        selected_piece = self._board.get_piece(*self._selected)

        if not piece.is_empty and piece.color == selected_piece.color:
            self._selected = (row, col)
            return

        if not self._board.can_move_piece(*self._selected, row, col):
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
