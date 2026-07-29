from __future__ import annotations

from io import StringIO

import pytest

from kungfu_chess.texttests.script_runner import main, run


class TestTextScripts:
    def _run(self, lines: list[str]) -> str:
        output = StringIO()
        run(lines, output=output)
        return output.getvalue()

    # ── Iteration 1 ──────────────────────────────────────────────────────────
    def test_board_then_print(self):
        out = self._run(["Board", "wK .", ". bK", "print board"])
        assert out == 'wK .\n. bK\n'

    def test_default_output_stream_is_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        run(["Board", "wK .", "print board"])

        assert capsys.readouterr().out == "wK .\n"

    def test_wait_before_board_is_ignored_and_later_commands_still_run(self) -> None:
        out = self._run(["wait 1000", "Board", "wK .", "print board"])

        assert out == "wK .\n"

    def test_main_reads_from_explicit_stream_and_writes_to_explicit_stream(
        self,
    ) -> None:
        input_stream = StringIO("Board:\nwK .\nCommands:\nprint board\n")
        output = StringIO()

        main(input_stream=input_stream, output=output)

        assert output.getvalue() == "wK .\n"

    # ── Iteration 5 ──────────────────────────────────────────────────────────
    def test_move_updates_board_at_first_cell_boundary(self):
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
        assert out == '. . .\n. wR .\n. . bK\n'

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
        assert out == '. . .\n. wR .\n. . bK\n. . .\n. . .\n. wR bK\n'

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
        assert out == '. . . wR\n. . . .\n'

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

        assert out == '. . wR\n. . .\n. . bR\n'

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

        assert out == '. . .\nwK . .\n. . .\n'

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

        assert out == '. wK .\n'

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

        assert out == 'wK .\n'

    @pytest.mark.parametrize(
        ("lines", "reason"),
        [
            (["Board:", "wK xZ", ". .", "Commands:"], "UNKNOWN_TOKEN"),
            (["Board:", "wK . .", ". bK", "Commands:"], "ROW_WIDTH_MISMATCH"),
        ],
    )
    def test_invalid_board_reports_canonical_error(
        self, lines: list[str], reason: str
    ) -> None:
        """Preserve parser errors through the complete text adapter path."""
        assert self._run(lines) == f'ERROR {reason}\n'

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
        assert out == '. . wR\n. . wN\n. . .\n'

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
        assert out == '. . wR\n. . wN\n. . .\n. . wR\n. . wN\n. . .\n'
