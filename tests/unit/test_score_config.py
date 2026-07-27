from __future__ import annotations

import json
from pathlib import Path

import pytest

from kungfu_chess.game_config import load_game_config

PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}


def _write_config(path: Path, piece_values: object) -> None:
    path.write_text(
        json.dumps(
            {
                "short_cooldown_ms": 2000,
                "long_cooldown_ms": 10000,
                "piece_values": piece_values,
            }
        ),
        encoding="utf-8",
    )


def test_piece_values_load_from_configuration(tmp_path: Path) -> None:
    path = tmp_path / "game_config.json"
    _write_config(path, PIECE_VALUES)

    config = load_game_config(path)

    assert dict(config.piece_values) == PIECE_VALUES


@pytest.mark.parametrize("invalid_value", (-1, 1.5, True, "3"))
def test_piece_values_reject_negative_and_non_integer_values(
    tmp_path: Path, invalid_value: object
) -> None:
    path = tmp_path / "game_config.json"
    values = dict(PIECE_VALUES)
    values["N"] = invalid_value
    _write_config(path, values)

    with pytest.raises((TypeError, ValueError), match="N"):
        load_game_config(path)


def test_zero_piece_value_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "game_config.json"
    _write_config(path, PIECE_VALUES)

    assert load_game_config(path).piece_values["K"] == 0


@pytest.mark.parametrize(
    "invalid_values",
    (
        {"P": 1},
        {**PIECE_VALUES, "X": 4},
        [],
    ),
)
def test_piece_values_require_exactly_all_supported_kinds(
    tmp_path: Path, invalid_values: object
) -> None:
    path = tmp_path / "game_config.json"
    _write_config(path, invalid_values)

    with pytest.raises((TypeError, ValueError), match="piece_values"):
        load_game_config(path)
