from __future__ import annotations

import pytest

from kungfu_chess.model.game_state import GameSnapshot, PieceSnapshot, RestSnapshot
from kungfu_chess.model.position import Position


class TestRestSnapshot:
    def test_rest_snapshot_is_immutable(self) -> None:
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="long_rest", elapsed_ms=100, duration_ms=10000
        )

        with pytest.raises(AttributeError):
            setattr(rest, "elapsed_ms", 200)  # noqa: B010

    def test_rest_snapshot_exposes_kind_elapsed_and_duration(self) -> None:
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="short_rest", elapsed_ms=250, duration_ms=2000
        )

        assert rest.piece_id == "wP_1_0"
        assert rest.rest_kind == "short_rest"
        assert rest.elapsed_ms == 250
        assert rest.duration_ms == 2000


class TestGameSnapshotRests:
    def test_rests_defaults_to_empty_tuple(self) -> None:
        snapshot = GameSnapshot(pieces=(), motions=(), game_over=False, width=1, height=1)

        assert snapshot.rests == ()

    def test_rests_collection_is_immutable(self) -> None:
        piece = PieceSnapshot(
            id="wP_1_0",
            color="w",
            kind="P",
            cell=Position(1, 0),
            state="long_rest",
        )
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        snapshot = GameSnapshot(
            pieces=(piece,), motions=(), rests=(rest,), game_over=False, width=8, height=8
        )

        with pytest.raises(AttributeError):
            setattr(snapshot, "rests", ())  # noqa: B010
        with pytest.raises(AttributeError):
            getattr(snapshot.rests, "append")(rest)  # noqa: B009
