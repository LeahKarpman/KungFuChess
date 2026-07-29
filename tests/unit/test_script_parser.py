from __future__ import annotations

import pytest

from kungfu_chess.texttests.script_parser import parse_script


def test_empty_script_has_no_commands() -> None:
    assert parse_script([]) == []


def test_board_section_may_be_empty_at_end_of_input() -> None:
    assert parse_script(["Board:"]) == [("board", [])]


def test_empty_line_ends_board_without_becoming_a_command() -> None:
    commands = parse_script(["Board:", "wK .", "", "print board"])

    assert commands == [("board", ["wK ."]), ("print_board",)]


def test_unknown_lines_are_ignored_without_stopping_parsing() -> None:
    commands = parse_script(["unknown command", "print board"])

    assert commands == [("print_board",)]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("click 10 20", ("click", 10, 20)),
        ("jump -1 20", ("jump", -1, 20)),
        ("wait 250", ("wait", 250)),
    ],
)
def test_integer_commands_preserve_their_arguments(
    line: str, expected: tuple[object, ...]
) -> None:
    assert parse_script([line]) == [expected]


@pytest.mark.parametrize(
    "line",
    [
        "click 10",
        "click 10 20 30",
        "click x 20",
        "jump 10",
        "jump 10 y",
        "wait",
        "wait 10 20",
        "wait later",
    ],
)
def test_malformed_integer_commands_are_ignored(line: str) -> None:
    assert parse_script([line]) == []
