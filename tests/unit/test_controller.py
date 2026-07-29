from __future__ import annotations

from kungfu_chess.engine.game_engine import GameEngine, JumpResult, MoveResult
from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.input.controller import Controller
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.game_state import GameSnapshot, PieceSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine


def _setup(lines: list[str]) -> tuple[Controller, GameEngine]:
    """Build a controller and its real engine for a small board."""
    board = parse_board(lines)
    engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
    mapper = BoardMapper(board.width, board.height)
    controller = Controller(mapper, engine)
    return controller, engine


class FakeControllerEngine:
    """Expose only the engine behavior consumed by Controller and record commands."""

    def __init__(
        self,
        pieces: tuple[PieceSnapshot, ...] = (),
        move_result: MoveResult = MoveResult(ok=False, reason="rejected"),
        jump_result: JumpResult = JumpResult(ok=False, reason="rejected"),
    ) -> None:
        self.game_over = False
        self._snapshot = GameSnapshot(
            pieces=pieces,
            motions=(),
            rests=(),
            game_over=False,
            width=3,
            height=3,
        )
        self.move_result = move_result
        self.jump_result = jump_result
        self.snapshot_calls = 0
        self.request_move_calls: list[tuple[Position, Position]] = []
        self.jump_calls: list[Position] = []

    def snapshot(self) -> GameSnapshot:
        self.snapshot_calls += 1
        return self._snapshot

    def request_move(self, src: Position, dst: Position) -> MoveResult:
        self.request_move_calls.append((src, dst))
        return self.move_result

    def jump(self, pos: Position) -> JumpResult:
        self.jump_calls.append(pos)
        return self.jump_result


def _piece_snapshot(cell: Position) -> PieceSnapshot:
    return PieceSnapshot(
        id="piece-a",
        color="w",
        kind="R",
        cell=cell,
        state="idle",
    )


class RecordingEngine:
    """Record controller commands while delegating all game behavior to a real engine."""

    def __init__(self, engine: GameEngine) -> None:
        self._engine = engine
        self.request_move_calls: list[tuple[Position, Position]] = []
        self.jump_calls: list[Position] = []

    @property
    def game_over(self) -> bool:
        return self._engine.game_over

    def snapshot(self):
        return self._engine.snapshot()

    def request_move(self, src: Position, dst: Position) -> MoveResult:
        self.request_move_calls.append((src, dst))
        return self._engine.request_move(src, dst)

    def jump(self, pos: Position) -> JumpResult:
        self.jump_calls.append(pos)
        return self._engine.jump(pos)

    def wait(self, elapsed_ms: int) -> None:
        self._engine.wait(elapsed_ms)

    def consume_events(self):
        return self._engine.consume_events()


def _finish_game_with_existing_selection() -> tuple[Controller, RecordingEngine]:
    """End a real game while the controller still owns a selection."""
    board = parse_board(["wR . bR . wK"])
    real_engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
    engine = RecordingEngine(real_engine)
    controller = Controller(BoardMapper(board.width, board.height), engine)
    controller.click(50, 50)
    engine.request_move(Position(0, 2), Position(0, 4))
    engine.wait(2000)
    assert engine.game_over
    engine.request_move_calls.clear()
    return controller, engine


class TestController:
    """Verify click interpretation and selection state."""

    def test_first_click_on_piece_selects(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(50, 50)

        assert result.action == 'selected'
        assert controller.selected == Position(0, 0)

    def test_first_click_on_empty_ignored(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(150, 50)

        assert result.action == 'ignored'
        assert controller.selected is None

    def test_outside_click_no_selection_ignored(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(9999, 9999)

        assert result.action == 'ignored'

    def test_outside_click_with_selection_cancels(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)

        result = controller.click(9999, 9999)

        assert result.action == 'cancelled'
        assert controller.selected is None

    def test_clicking_selected_piece_cancels_selection(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.click(50, 50)

        assert result.action == 'cancelled'
        assert result.position == Position(0, 0)
        assert controller.selected is None

    def test_clicking_selected_piece_does_not_request_move(self) -> None:
        fake_engine = FakeControllerEngine(
            pieces=(_piece_snapshot(Position(0, 0)),)
        )
        controller = Controller(BoardMapper(3, 1), fake_engine)
        controller.click(50, 50)

        result = controller.click(50, 50)

        assert result.action == 'cancelled'
        assert fake_engine.request_move_calls == []

    def test_clicking_selected_piece_leaves_engine_state_unchanged(self) -> None:
        controller, engine = _setup(["wR . ."])
        controller.click(50, 50)
        snapshot_before = engine.snapshot()

        controller.click(50, 50)

        assert engine.snapshot() == snapshot_before
        assert engine.consume_events() == ()

    def test_clicking_different_friendly_piece_replaces_selection(self) -> None:
        controller, _ = _setup(["wR wN ."])
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.click(150, 50)

        assert result.action == 'selected'
        assert result.position == Position(0, 1)
        assert controller.selected == Position(0, 1)

    def test_second_inboard_click_sends_move_and_clears_selection(self) -> None:
        fake_engine = FakeControllerEngine(
            pieces=(_piece_snapshot(Position(0, 0)),),
            move_result=MoveResult(ok=True, reason="ok"),
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, fake_engine)
        controller.click(50, 50)

        result = controller.click(150, 50)

        assert result.action == 'move_requested'
        assert fake_engine.request_move_calls == [(Position(0, 0), Position(0, 1))]
        assert controller.selected is None

    def test_rejected_move_preserves_selection(self) -> None:
        """A move rejected by the engine must not clear the current selection.

        Selection is cleared only when the requested action is accepted and
        actually starts; this supersedes the old expectation that selection
        was cleared regardless of validity.
        """
        fake_engine = FakeControllerEngine(
            pieces=(_piece_snapshot(Position(0, 0)),),
            move_result=MoveResult(
                ok=False,
                reason="illegal_piece_move",
            ),
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, fake_engine)
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.click(150, 50)

        assert result.action == 'move_requested'
        assert controller.selected == Position(0, 0)

    def test_rejected_move_via_real_engine_preserves_selection(self) -> None:
        """Same rule, exercised through the real engine and rule engine.

        A knight on a single-row board has no legal destination, so the
        engine rejects the move with 'illegal_piece_move' and selection survives.
        """
        controller, _ = _setup(["wN . ."])
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.click(150, 50)

        assert result.action == 'move_requested'
        assert controller.selected == Position(0, 0)

    def test_moving_piece_cannot_be_selected(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 2))

        result = controller.click(50, 50)

        assert result.action == 'ignored'
        assert controller.selected is None

    def test_selected_piece_can_target_moving_enemy(self) -> None:
        """Forward a moving enemy cell as the selected piece's destination."""
        controller, engine = _setup([". . .", "wK bR .", ". . ."])
        engine.jump(Position(1, 0))
        controller.click(150, 150)

        result = controller.click(50, 150)

        assert result.action == 'move_requested'
        assert controller.selected is None

    def test_jump_maps_pixels_and_delegates_to_engine(self) -> None:
        """Forward an in-board jump request without applying game rules."""
        fake_engine = FakeControllerEngine(
            jump_result=JumpResult(ok=True, reason="ok")
        )
        controller = Controller(BoardMapper(3, 3), fake_engine)

        result = controller.jump(150, 250)

        assert result.action == 'jump_requested'
        assert result.position == Position(2, 1)
        assert fake_engine.jump_calls == [Position(2, 1)]

    def test_jump_does_not_call_snapshot_to_decide_legality(self) -> None:
        fake_engine = FakeControllerEngine(
            jump_result=JumpResult(ok=True, reason="ok")
        )
        controller = Controller(BoardMapper(3, 3), fake_engine)

        controller.jump(150, 250)

        assert fake_engine.snapshot_calls == 0

    def test_jump_outside_board_is_ignored(self) -> None:
        """Reject an out-of-board jump before it reaches the game engine."""
        fake_engine = FakeControllerEngine()
        controller = Controller(BoardMapper(3, 3), fake_engine)

        result = controller.jump(-1, 50)

        assert result.action == 'ignored'
        assert fake_engine.jump_calls == []

    def test_right_click_outside_board_preserves_selection_and_does_not_call_engine(
        self,
    ) -> None:
        fake_engine = FakeControllerEngine(
            pieces=(_piece_snapshot(Position(0, 0)),)
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, fake_engine)
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.jump(-1, 50)

        assert result.action == 'ignored'
        assert controller.selected == Position(0, 0)
        assert fake_engine.jump_calls == []

    def test_valid_jump_clears_current_selection(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.jump(50, 50)

        assert result.action == 'jump_requested'
        assert controller.selected is None

    def test_valid_jump_by_piece_b_clears_selection_belonging_to_piece_a(self) -> None:
        """An accepted jump clears the selection even for an unrelated piece."""
        controller, _ = _setup(["wR . wN"])
        controller.click(50, 50)  # select piece A (wR) at (0, 0)
        assert controller.selected == Position(0, 0)

        controller.jump(250, 50)  # piece B (wN) at (0, 2) jumps

        assert controller.selected is None

    def test_rejected_jump_preserves_current_selection(self) -> None:
        fake_engine = FakeControllerEngine(
            pieces=(_piece_snapshot(Position(0, 0)),),
            jump_result=JumpResult(
                ok=False, reason="no_piece_at_position"
            ),
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, fake_engine)
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.jump(150, 50)

        assert result.action == 'jump_requested'
        assert controller.selected == Position(0, 0)

    def test_jump_on_empty_cell_preserves_current_selection(self) -> None:
        """Let the engine and rules reject an in-board jump onto an empty cell."""
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        assert controller.selected == Position(0, 0)

        result = controller.jump(150, 50)  # (0, 1) is empty

        assert result.action == 'jump_requested'
        assert controller.selected == Position(0, 0)

    def test_busy_piece_jump_rejection_preserves_current_selection(self) -> None:
        controller, engine = _setup(["wR . wN"])
        controller.click(250, 50)  # select wN at (0, 2)
        assert controller.selected == Position(0, 2)
        engine.request_move(Position(0, 0), Position(0, 1))  # wR busy, still on board

        result = controller.jump(50, 50)  # attempt to jump the busy wR

        assert result.action == 'jump_requested'
        assert controller.selected == Position(0, 2)


class TestControllerGameOver:
    """Verify that terminal games ignore input without mutating engine state."""

    def test_existing_selection_clears_when_selected_is_next_read(self) -> None:
        controller, engine = _finish_game_with_existing_selection()

        assert controller.selected is None
        assert engine.game_over

    def test_left_click_on_piece_or_empty_cell_does_not_select(self) -> None:
        controller, _ = _finish_game_with_existing_selection()

        piece_result = controller.click(50, 50)
        empty_cell_result = controller.click(150, 50)

        assert piece_result.action == 'ignored'
        assert empty_cell_result.action == 'ignored'
        assert controller.selected is None

    def test_left_click_does_not_request_move_or_change_engine_state(self) -> None:
        controller, engine = _finish_game_with_existing_selection()
        engine.consume_events()
        snapshot_before = engine.snapshot()

        result = controller.click(150, 50)

        assert result.action == 'ignored'
        assert engine.request_move_calls == []
        assert engine.snapshot() == snapshot_before
        assert engine.consume_events() == ()

    def test_right_click_does_not_request_jump_or_change_engine_state(self) -> None:
        controller, engine = _finish_game_with_existing_selection()
        engine.consume_events()
        snapshot_before = engine.snapshot()

        result = controller.jump(50, 50)

        assert result.action == 'ignored'
        assert engine.jump_calls == []
        assert engine.snapshot() == snapshot_before
        assert engine.consume_events() == ()

    def test_left_click_selects_piece_while_game_is_active(self) -> None:
        controller, engine = _setup(["wR . ."])

        result = controller.click(50, 50)

        assert not engine.game_over
        assert result.action == 'selected'
        assert controller.selected == Position(0, 0)


class TestControllerCooldownSelection:
    """Verify that resting pieces follow the same selection rules as moving ones."""

    def test_resting_piece_cannot_be_selected(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # wR now long_rest at (0, 1)

        result = controller.click(150, 50)

        assert result.action == 'ignored'
        assert controller.selected is None

    def test_clicking_friendly_resting_piece_preserves_prior_selection(self) -> None:
        controller, engine = _setup(["wR . wN"])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # wR now long_rest at (0, 1); wN stays idle at (0, 2)

        select_result = controller.click(250, 50)
        assert select_result.action == 'selected'
        assert controller.selected == Position(0, 2)

        result = controller.click(150, 50)

        assert result.action == 'ignored'
        assert controller.selected == Position(0, 2)

    def test_enemy_resting_piece_remains_a_valid_destination(self) -> None:
        controller, engine = _setup(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)  # wR now long_rest at (0, 2)

        controller.click(350, 50)  # select bR at (0, 3)
        result = controller.click(250, 50)  # target the resting enemy at (0, 2)

        assert result.action == 'move_requested'
        assert controller.selected is None


class TestControllerSelectionIdentity:
    """Verify selection survives by piece identity, not by stale cell position.

    Selection must not silently keep pointing at a cell whose original
    occupant was captured in place by the opponent — otherwise a later
    click can be misattributed to whatever piece now sits on that cell.
    """

    def test_selected_property_self_heals_after_selected_piece_is_captured(
        self,
    ) -> None:
        controller, engine = _setup(["wR . bR"])
        controller.click(50, 50)  # select wR at (0, 0)
        assert controller.selected == Position(0, 0)

        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)

        assert controller.selected is None

    def test_clicking_another_friendly_piece_reselects_immediately_after_capture(
        self,
    ) -> None:
        """The stale selection must not hijack an unrelated piece's move.

        Before selection was tracked by piece id, this click fell through to
        the final branch and requested a move for the captured cell's new
        (enemy) occupant instead of reselecting the clicked friendly piece —
        and since that request was rejected, selection stayed stuck forever.
        """
        controller, engine = _setup(["wR . bR . wN"])
        controller.click(50, 50)  # select wR at (0, 0)
        assert controller.selected == Position(0, 0)

        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)  # bR now rests at (0, 0)

        result = controller.click(450, 50)  # click own knight at (0, 4)

        assert result.action == 'selected'
        assert controller.selected == Position(0, 4)

    def test_reselection_after_capture_can_be_toggled_across_repeated_clicks(
        self,
    ) -> None:
        controller, engine = _setup(["wR . bR . wN"])
        controller.click(50, 50)  # select wR at (0, 0)
        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)

        first_result = controller.click(450, 50)  # select own knight at (0, 4)
        second_result = controller.click(450, 50)  # cancel that selection
        third_result = controller.click(450, 50)  # select it again

        assert first_result.action == 'selected'
        assert second_result.action == 'cancelled'
        assert third_result.action == 'selected'
        assert controller.selected == Position(0, 4)

    def test_selection_works_immediately_after_rest_completion(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # long_rest starts
        engine.wait(10000)  # long_rest completes -> idle

        result = controller.click(150, 50)

        assert result.action == 'selected'
        assert controller.selected == Position(0, 1)
