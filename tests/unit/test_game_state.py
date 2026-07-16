from __future__ import annotations

import unittest

from kungfu_chess.model.game_state import GameSnapshot, PieceSnapshot, RestSnapshot
from kungfu_chess.model.position import Position


class TestRestSnapshot(unittest.TestCase):
    def test_rest_snapshot_is_immutable(self) -> None:
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="long_rest", elapsed_ms=100, duration_ms=10000
        )

        with self.assertRaises(AttributeError):
            setattr(rest, "elapsed_ms", 200)

    def test_rest_snapshot_exposes_kind_elapsed_and_duration(self) -> None:
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="short_rest", elapsed_ms=250, duration_ms=2000
        )

        self.assertEqual(rest.piece_id, "wP_1_0")
        self.assertEqual(rest.rest_kind, "short_rest")
        self.assertEqual(rest.elapsed_ms, 250)
        self.assertEqual(rest.duration_ms, 2000)


class TestGameSnapshotRests(unittest.TestCase):
    def test_rests_defaults_to_empty_tuple(self) -> None:
        snapshot = GameSnapshot(pieces=(), motions=(), game_over=False, width=1, height=1)

        self.assertEqual(snapshot.rests, ())

    def test_rests_collection_is_immutable(self) -> None:
        piece = PieceSnapshot(id="wP_1_0", color="w", kind="P", cell=Position(1, 0), state="long_rest")
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        snapshot = GameSnapshot(
            pieces=(piece,), motions=(), rests=(rest,), game_over=False, width=8, height=8
        )

        with self.assertRaises(AttributeError):
            setattr(snapshot, "rests", ())
        with self.assertRaises(AttributeError):
            snapshot.rests.append(rest)


if __name__ == "__main__":
    unittest.main()
