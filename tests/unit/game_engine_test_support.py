from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine


def make_engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board
