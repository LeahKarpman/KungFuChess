from __future__ import annotations
from typing import Literal, Union


BoardCommand = tuple[Literal['board'], list[str]]
PrintBoardCommand = tuple[Literal['print_board']]
ClickCommand = tuple[Literal['click'], int, int]
JumpCommand = tuple[Literal['jump'], int, int]
WaitCommand = tuple[Literal['wait'], int]
ScriptCommand = Union[
    BoardCommand,
    PrintBoardCommand,
    ClickCommand,
    JumpCommand,
    WaitCommand,
]


def _is_command_or_section(line: str) -> bool:
    return line in ('print board', 'Board:', 'Board', 'Commands:') or \
           line.startswith(('click ', 'wait ', 'jump '))


def parse_script(lines: list[str]) -> list[ScriptCommand]:
    commands: list[ScriptCommand] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ('Board:', 'Board'):
            i += 1
            board_lines: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                if current == '' or _is_command_or_section(current):
                    break
                board_lines.append(current)
                i += 1
            commands.append(('board', board_lines))
        elif line == 'Commands:':
            i += 1
        elif line == 'print board':
            commands.append(('print_board',))
            i += 1
        elif line.startswith('click '):
            parts = line.split()
            commands.append(('click', int(parts[1]), int(parts[2])))
            i += 1
        elif line.startswith('jump '):
            parts = line.split()
            commands.append(('jump', int(parts[1]), int(parts[2])))
            i += 1
        elif line.startswith('wait '):
            commands.append(('wait', int(line.split()[1])))
            i += 1
        else:
            i += 1
    return commands
