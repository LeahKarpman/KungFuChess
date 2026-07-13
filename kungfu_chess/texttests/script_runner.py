from __future__ import annotations
import sys

from .script_parser import parse_script
from ..io.board_parser import parse_board
from ..io.board_mapper import BoardMapper
from ..engine.rule_engine import RuleEngine
from ..engine.real_time_arbiter import RealTimeArbiter
from ..engine.game_engine import GameEngine
from ..controller.controller import Controller


def run(lines):
    commands = parse_script(lines)
    engine = None
    controller = None
    mapper = None

    for cmd in commands:
        if cmd[0] == 'board':
            try:
                board = parse_board(cmd[1])
            except ValueError as e:
                sys.stdout.write('ERROR ' + str(e) + '\n')
                engine = None
                controller = None
                continue
            engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
            mapper = BoardMapper(board.width, board.height)
            controller = Controller(mapper, engine)

        elif cmd[0] == 'print_board' and engine is not None:
            sys.stdout.write(engine.board_text() + '\n')

        elif cmd[0] == 'click' and controller is not None:
            controller.click(cmd[1], cmd[2])

        elif cmd[0] == 'jump' and engine is not None:
            # jump מופנה ישירות ל-GameEngine — אחריות תנועה, לא קלט משתמש
            pos = mapper.pixel_to_cell(cmd[1], cmd[2])
            if pos is not None:
                engine.jump(pos)

        elif cmd[0] == 'wait' and engine is not None:
            engine.wait(cmd[1])


def main():
    lines = [line.rstrip('\n') for line in sys.stdin]
    run(lines)
