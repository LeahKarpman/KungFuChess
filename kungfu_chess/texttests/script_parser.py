from __future__ import annotations
from typing import List, Literal, Tuple, Union


BoardCommand = Tuple[Literal["board"], List[str]]
PrintBoardCommand = Tuple[Literal["print_board"]]
ClickCommand = Tuple[Literal["click"], int, int]
JumpCommand = Tuple[Literal["jump"], int, int]
WaitCommand = Tuple[Literal["wait"], int]
ScriptCommand = Union[
    BoardCommand,
    PrintBoardCommand,
    ClickCommand,
    JumpCommand,
    WaitCommand,
]


def _is_command_or_section(line: str) -> bool:
    return line in ("print board", "Board:", "Board", "Commands:") or line.startswith(
        ("click ", "wait ", "jump ")
    )


def _parse_integer_arguments(
    line: str,
    argument_count: int,
) -> tuple[int, ...] | None:
    """Return exact integer arguments, or None for a malformed command."""
    parts = line.split()
    if len(parts) != argument_count + 1:
        return None

    try:
        return tuple(int(value) for value in parts[1:])
    except ValueError:
        return None


def parse_script(lines: list[str]) -> list[ScriptCommand]:
    """Parse supported text commands while ignoring malformed input lines."""
    commands: list[ScriptCommand] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ("Board:", "Board"):
            i += 1
            board_lines: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                if current == "" or _is_command_or_section(current):
                    break
                board_lines.append(current)
                i += 1
            commands.append(("board", board_lines))
        elif line == "Commands:":
            i += 1
        elif line == "print board":
            commands.append(("print_board",))
            i += 1
        elif line.startswith("click "):
            arguments = _parse_integer_arguments(line, 2)
            if arguments is not None:
                commands.append(("click", arguments[0], arguments[1]))
            i += 1
        elif line.startswith("jump "):
            arguments = _parse_integer_arguments(line, 2)
            if arguments is not None:
                commands.append(("jump", arguments[0], arguments[1]))
            i += 1
        elif line.startswith("wait "):
            arguments = _parse_integer_arguments(line, 1)
            if arguments is not None:
                commands.append(("wait", arguments[0]))
            i += 1
        else:
            i += 1
    return commands
