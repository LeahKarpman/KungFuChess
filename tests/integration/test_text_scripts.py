from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from kungfu_chess.texttests.script_runner import run


class TestTextScripts(unittest.TestCase):
    def _run(self, lines: list[str]) -> str:
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            run(lines)
            return mock_out.getvalue()

    # ── Iteration 1 ──────────────────────────────────────────────────────────
    def test_board_then_print(self):
        out = self._run(["Board", "wK .", ". bK", "print board"])
        self.assertEqual(out, "wK .\n. bK\n")

    # ── Iteration 5 ──────────────────────────────────────────────────────────
    def test_move_before_arrival_board_unchanged(self):
        lines = [
            "Board",
            ". wR .",
            ". . .",
            ". . bK",
            "click 150 50",
            "click 150 250",
            "wait 1000",
            "print board",
        ]
        out = self._run(lines)
        self.assertEqual(out, ". wR .\n. . .\n. . bK\n")

    def test_move_after_arrival_board_updated(self):
        lines = [
            "Board",
            ". wR .",
            ". . .",
            ". . bK",
            "click 150 50",
            "click 150 250",
            "wait 1000",
            "print board",
            "wait 1000",
            "print board",
        ]
        out = self._run(lines)
        self.assertEqual(out, ". wR .\n. . .\n. . bK\n. . .\n. . .\n. wR bK\n")

    def test_second_move_while_motion_active_rejected(self):
        # A moving piece cannot be redirected before it arrives.
        lines = [
            "Board",
            ". wR . .",
            ". . . .",
            "click 150 50",
            "click 350 50",
            "click 150 50",
            "wait 2000",
            "print board",
        ]
        out = self._run(lines)
        self.assertEqual(out, ". . . wR\n. . . .\n")

    def test_distinct_pieces_move_concurrently(self):
        lines = [
            "Board",
            "wR . .",
            ". . .",
            "bR . .",
            "click 50 50",
            "click 250 50",
            "click 50 250",
            "click 250 250",
            "wait 2000",
            "print board",
        ]

        out = self._run(lines)

        self.assertEqual(out, ". . wR\n. . .\n. . bR\n")

    def test_airborne_piece_captures_arriving_enemy(self):
        """Exercise the complete click route for an airborne capture."""
        lines = [
            "Board:",
            ". . .",
            "wK bR .",
            ". . .",
            "Commands:",
            "jump 50 150",
            "click 150 150",
            "click 50 150",
            "wait 1000",
            "print board",
        ]

        out = self._run(lines)

        self.assertEqual(out, ". . .\nwK . .\n. . .\n")

    def test_print_board_keeps_airborne_piece_visible_before_landing(self):
        """Render the pre-arrival state from the public game snapshot."""
        lines = [
            "Board:",
            ". wK .",
            "Commands:",
            "jump 150 50",
            "print board",
        ]

        out = self._run(lines)

        self.assertEqual(out, ". wK .\n")

    def test_malformed_commands_are_ignored_without_stopping_script(self):
        """Continue to valid commands after malformed text input."""
        lines = [
            "Board:",
            "wK .",
            "Commands:",
            "click 50",
            "jump x 50",
            "wait abc",
            "click 50 50 extra",
            "print board",
        ]

        out = self._run(lines)

        self.assertEqual(out, "wK .\n")

    def test_invalid_board_reports_canonical_error(self) -> None:
        """Preserve parser errors through the complete text adapter path."""
        cases = [
            (["Board:", "wK xZ", ". .", "Commands:"], "UNKNOWN_TOKEN"),
            (["Board:", "wK . .", ". bK", "Commands:"], "ROW_WIDTH_MISMATCH"),
        ]

        for lines, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self._run(lines), f"ERROR {reason}\n")

    # ── Iteration 6 ──────────────────────────────────────────────────────────
    def test_capture_removes_enemy_on_arrival(self):
        lines = [
            "Board",
            "wR . bK",
            ". . wN",
            ". . .",
            "click 50 50",
            "click 250 50",
            "wait 2000",
            "print board",
        ]
        out = self._run(lines)
        self.assertEqual(out, ". . wR\n. . wN\n. . .\n")

    def test_game_over_blocks_further_moves(self):
        lines = [
            "Board",
            "wR . bK",
            ". . wN",
            ". . .",
            "click 50 50",
            "click 250 50",
            "wait 2000",
            "print board",
            "click 250 150",
            "click 50 250",
            "wait 2000",
            "print board",
        ]
        out = self._run(lines)
        # The board does not change after the king is captured.
        self.assertEqual(out, ". . wR\n. . wN\n. . .\n. . wR\n. . wN\n. . .\n")
