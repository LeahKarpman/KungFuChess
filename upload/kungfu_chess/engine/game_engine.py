from __future__ import annotations
from dataclasses import dataclass
from ..model.position import Position
from .rule_engine import RuleEngine
from .real_time_arbiter import RealTimeArbiter, MS_PER_CELL
from .game_snapshot import GameSnapshot, PieceSnapshot, MotionSnapshot


@dataclass(frozen=True)
class MoveResult:
    ok: bool
    reason: str


@dataclass
class _Jump:
    piece_id: str
    landing: Position
    elapsed_ms: int = 0
    duration_ms: int = MS_PER_CELL


class GameEngine:
    def __init__(self, board, rule_engine=None, arbiter=None):
        self._board = board
        self._rules = rule_engine or RuleEngine()
        self._arbiter = arbiter or RealTimeArbiter()
        self._game_over = False
        self._airborne = {}   # piece_id -> Piece
        self._jump = None     # _Jump | None

    @property
    def game_over(self):
        return self._game_over

    def request_move(self, src: Position, dst: Position) -> MoveResult:
        if self._game_over:
            return MoveResult(ok=False, reason='game_over')
        if self._arbiter.has_active_motion():
            return MoveResult(ok=False, reason='motion_in_progress')
        if self._jump is not None and dst == self._jump.landing:
            piece = self._board.get_piece(src)
            jumper = self._airborne.get(self._jump.piece_id)
            if jumper is not None and piece is not None and piece.color == jumper.color:
                return MoveResult(ok=False, reason='landing_reserved')
        validation = self._rules.validate_move(self._board, src, dst)
        if not validation.ok:
            return MoveResult(ok=False, reason=validation.reason)
        piece = self._board.get_piece(src)
        self._arbiter.start_motion(piece.id, src, dst)
        return MoveResult(ok=True, reason='ok')

    def jump(self, pos: Position) -> None:
        """Remove a friendly piece from the board temporarily; it lands back after MS_PER_CELL."""
        if self._jump is not None:
            return
        piece = self._board.get_piece(pos)
        if piece is None or piece.color != 'w':
            return
        self._board.remove_piece(pos)
        self._airborne[piece.id] = piece
        self._jump = _Jump(piece_id=piece.id, landing=pos)

    def wait(self, ms: int) -> None:
        for event in self._arbiter.advance_time(ms):
            self._apply_arrival(event)
        self._advance_jump(ms)

    def _advance_jump(self, ms: int) -> None:
        if self._jump is None:
            return
        self._jump.elapsed_ms += ms
        if self._jump.elapsed_ms >= self._jump.duration_ms:
            piece = self._airborne.pop(self._jump.piece_id, None)
            landing = self._jump.landing
            self._jump = None
            if piece is None:
                return
            target = self._board.get_piece(landing)
            if target and target.color != piece.color:
                # jumper captures enemies only; friendly pieces are not displaced
                target.state = 'captured'
                self._board.remove_piece(landing)
                if target.kind == 'K':
                    self._game_over = True
            if not self._board.get_piece(landing):
                piece.cell = landing
                self._board.add_piece(piece)

    def _apply_arrival(self, event) -> None:
        piece = self._board.get_piece(event.source)
        if piece is not None:
            self._board.remove_piece(event.source)
        else:
            piece = self._airborne.pop(event.piece_id, None)
        if piece is None:
            return
        target = self._board.get_piece(event.destination)
        if target:
            target.state = 'captured'
            self._board.remove_piece(event.destination)
            if target.kind == 'K':
                self._game_over = True
        piece.cell = event.destination
        self._board.add_piece(piece)
        self._try_promote(piece)

    def _try_promote(self, piece) -> None:
        if piece.kind != 'P':
            return
        promotion_row = 0 if piece.color == 'w' else self._board.height - 1
        if piece.cell.row == promotion_row:
            piece.kind = 'Q'

    def snapshot(self, selected=None) -> GameSnapshot:
        pieces = tuple(
            PieceSnapshot(p.id, p.color, p.kind, p.cell, p.state)
            for p in self._board._cells.values()
        )
        motions = ()
        m = self._arbiter.current_motion()
        if m:
            motions = (MotionSnapshot(m.piece_id, m.source, m.destination,
                                      m.elapsed_ms, m.duration_ms),)
        return GameSnapshot(
            pieces=pieces,
            motions=motions,
            selected=selected,
            game_over=self._game_over,
            width=self._board.width,
            height=self._board.height,
        )

    def board_text(self) -> str:
        from ..io.board_printer import print_board
        return print_board(self._board)
