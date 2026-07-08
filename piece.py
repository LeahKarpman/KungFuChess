EMPTY_TOKEN = "."

VALID_COLORS = {"w", "b"}

VALID_KINDS = {"K", "Q", "R", "B", "N", "P"}


def _is_valid_king_move(dr, dc):
    return max(abs(dr), abs(dc)) == 1


def _is_valid_rook_move(dr, dc):
    return dr == 0 or dc == 0


def _is_valid_bishop_move(dr, dc):
    return abs(dr) == abs(dc)


def _is_valid_queen_move(dr, dc):
    return _is_valid_rook_move(dr, dc) or _is_valid_bishop_move(dr, dc)


def _is_valid_knight_move(dr, dc):
    return {abs(dr), abs(dc)} == {1, 2}


_MOVEMENT_VALIDATORS = {
    "K": _is_valid_king_move,
    "R": _is_valid_rook_move,
    "B": _is_valid_bishop_move,
    "Q": _is_valid_queen_move,
    "N": _is_valid_knight_move,
}


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

    def can_move_to(self, from_row, from_col, to_row, to_col):
        validator = _MOVEMENT_VALIDATORS.get(self.kind)
        if validator is None:
            return False
        dr = to_row - from_row
        dc = to_col - from_col
        if dr == 0 and dc == 0:
            return False
        return validator(dr, dc)

    @staticmethod
    def is_valid_token(token):
        if token == EMPTY_TOKEN:
            return True
        if len(token) != 2:
            return False
        return token[0] in VALID_COLORS and token[1] in VALID_KINDS
