from __future__ import annotations
import sys

from .script_parser import parse_script
from ..io.board_parser import parse_board
from ..io.board_mapper import BoardMapper
from ..io.board_printer import print_snapshot
from ..engine.rule_engine import RuleEngine
from ..engine.real_time_arbiter import RealTimeArbiter
from ..engine.game_engine import GameEngine
from ..controller.controller import Controller


def run(lines: list[str]) -> None:
    commands = parse_script(lines)
    engine: GameEngine | None = None
    controller: Controller | None = None

    for cmd in commands:
        if cmd[0] == "board":
            try:
                board = parse_board(cmd[1])
            except ValueError as e:
                sys.stdout.write("ERROR " + str(e) + "\n")
                engine = None
                controller = None
                continue
            engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
            controller = Controller(
                BoardMapper(board.width, board.height),
                engine,
            )

        elif cmd[0] == "print_board" and engine is not None:
            sys.stdout.write(print_snapshot(engine.snapshot()) + "\n")

        elif cmd[0] == "click" and controller is not None:
            controller.click(cmd[1], cmd[2])

        elif cmd[0] == "jump" and controller is not None:
            controller.jump(cmd[1], cmd[2])

        elif cmd[0] == "wait" and engine is not None:
            engine.wait(cmd[1])


def main() -> None:
    lines = [line.rstrip("\n") for line in sys.stdin]
    run(lines)
