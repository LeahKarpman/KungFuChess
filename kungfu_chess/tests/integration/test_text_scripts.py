import unittest
from io import StringIO
from unittest.mock import patch
from kungfu_chess.texttests.script_runner import run


class TestTextScripts(unittest.TestCase):
    def _run(self, lines):
        with patch('sys.stdout', new_callable=StringIO) as mock_out:
            run(lines)
            return mock_out.getvalue()

    # ── Iteration 1 ──────────────────────────────────────────────────────────
    def test_board_then_print(self):
        out = self._run(['Board', 'wK .', '. bK', 'print board'])
        self.assertEqual(out, 'wK .\n. bK\n')

    # ── Iteration 5 ──────────────────────────────────────────────────────────
    def test_move_before_arrival_board_unchanged(self):
        lines = [
            'Board',
            '. wR .',
            '. . .',
            '. . bK',
            'click 150 50',
            'click 150 250',
            'wait 1000',
            'print board',
        ]
        out = self._run(lines)
        self.assertEqual(out, '. wR .\n. . .\n. . bK\n')

    def test_move_after_arrival_board_updated(self):
        lines = [
            'Board',
            '. wR .',
            '. . .',
            '. . bK',
            'click 150 50',
            'click 150 250',
            'wait 1000',
            'print board',
            'wait 1000',
            'print board',
        ]
        out = self._run(lines)
        self.assertEqual(out, '. wR .\n. . .\n. . bK\n. . .\n. . .\n. wR bK\n')

    def test_second_move_while_motion_active_rejected(self):
        # הרוק זז 2 תאים = 2000ms; ניסיון מהלך שני נדחה
        lines = [
            'Board',
            '. wR . .',
            '. . . .',
            'click 150 50',
            'click 350 50',
            'click 150 50',   # אין כלי שם עוד — ignored
            'wait 2000',
            'print board',
        ]
        out = self._run(lines)
        self.assertEqual(out, '. . . wR\n. . . .\n')

    # ── Iteration 6 ──────────────────────────────────────────────────────────
    def test_capture_removes_enemy_on_arrival(self):
        lines = [
            'Board',
            'wR . bK',
            '. . wN',
            '. . .',
            'click 50 50',
            'click 250 50',
            'wait 2000',
            'print board',
        ]
        out = self._run(lines)
        self.assertEqual(out, '. . wR\n. . wN\n. . .\n')

    def test_game_over_blocks_further_moves(self):
        lines = [
            'Board',
            'wR . bK',
            '. . wN',
            '. . .',
            'click 50 50',
            'click 250 50',
            'wait 2000',
            'print board',
            'click 250 150',
            'click 50 250',
            'wait 2000',
            'print board',
        ]
        out = self._run(lines)
        # לאחר לכידת המלך — הלוח לא משתנה
        self.assertEqual(out, '. . wR\n. . wN\n. . .\n. . wR\n. . wN\n. . .\n')
