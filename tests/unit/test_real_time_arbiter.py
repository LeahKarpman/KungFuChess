# pyright: reportOptionalMemberAccess=false

import pytest

from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.motion import Motion, calculate_route
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.realtime.rest import (
    DEFAULT_LONG_COOLDOWN_MS,
    DEFAULT_SHORT_COOLDOWN_MS,
    Rest,
)


class TestRealTimeArbiter:
    """Verify deterministic scheduling and completion of timed actions."""

    def setup_method(self) -> None:
        self.arbiter = RealTimeArbiter()
        self.src = Position(0, 0)
        self.dst = Position(0, 1)
        self.piece = Piece("wR_0_0", "w", "R", self.src)

    def test_no_active_actions_initially(self) -> None:
        assert self.arbiter.active_actions() == ()

    def test_start_motion_marks_piece_busy(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        assert self.arbiter.is_piece_busy(self.piece.id)

    def test_before_arrival_no_event(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(999)

        assert events == []
        assert self.arbiter.is_piece_busy(self.piece.id)

    def test_arrival_at_1000ms(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1000)

        assert len(events) == 1
        assert events[0].destination == self.dst
        # A completed motion stays authoritative (still busy) until the
        # caller explicitly acknowledges it via resolve_arrival — see
        # TestArrivalResolutionProtocol for the two-phase contract.
        assert self.arbiter.is_piece_busy(self.piece.id)

        self.arbiter.resolve_arrival(self.piece.id)

        assert not (self.arbiter.is_piece_busy(self.piece.id))

    def test_partial_then_remaining_wait(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        assert self.arbiter.advance_time(500) == []
        events = self.arbiter.advance_time(500)

        assert len(events) == 1

    def test_negative_time_does_not_rewind_active_action(self) -> None:
        """Keep simulated time monotonic when given a negative duration."""
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        assert self.arbiter.advance_time(500) == []
        assert self.arbiter.advance_time(-250) == []
        events = self.arbiter.advance_time(500)

        assert len(events) == 1
        assert events[0].piece.id == self.piece.id

    def test_two_cell_move_reports_each_cell_boundary(self) -> None:
        self.arbiter.start_motion(
            self.piece,
            Position(0, 0),
            Position(0, 2),
        )

        first = self.arbiter.advance_time(1000)
        assert first[0].source == Position(0, 0)
        assert first[0].destination == Position(0, 1)
        assert not (first[0].is_final)

        self.arbiter.resolve_arrival(self.piece.id)
        second = self.arbiter.advance_time(1000)

        assert second[0].source == Position(0, 1)
        assert second[0].destination == Position(0, 2)
        assert second[0].is_final

    def test_knight_transit_exposes_one_direct_visual_segment_and_one_arrival(
        self,
    ) -> None:
        source = Position(0, 0)
        destination = Position(2, 1)
        knight = Piece("wN_0_0", "w", "N", source)
        self.arbiter.start_motion(knight, source, destination)

        first_segment = self.arbiter.active_actions()[0]
        assert first_segment.source == Position(0, 0)
        assert first_segment.destination == destination
        assert first_segment.elapsed_ms == 0
        assert first_segment.duration_ms == 3000

        assert self.arbiter.advance_time(1000) == []
        second_segment = self.arbiter.active_actions()[0]
        assert second_segment.source == source
        assert second_segment.destination == destination
        assert second_segment.elapsed_ms == 1000
        assert second_segment.duration_ms == 3000
        assert second_segment.action_elapsed_ms == 1000

        assert self.arbiter.advance_time(1000) == []
        final_segment = self.arbiter.active_actions()[0]
        assert final_segment.source == source
        assert final_segment.destination == destination
        assert final_segment.elapsed_ms == 2000
        assert final_segment.duration_ms == 3000
        assert final_segment.action_elapsed_ms == 2000

        events = self.arbiter.advance_time(1000)

        assert len(events) == 1
        assert events[0].source == source
        assert events[0].destination == destination
        assert events[0].is_final
        assert self.arbiter.active_actions()[0].action_elapsed_ms == 3000

        self.arbiter.resolve_arrival(knight.id)
        assert not (self.arbiter.is_piece_busy(knight.id))

    def test_knight_final_arrival_keeps_sequence_order_against_same_time_move(
        self,
    ) -> None:
        knight = Piece("wN_0_0", "w", "N", Position(0, 0))
        rook = Piece("bR_3_0", "b", "R", Position(3, 0))
        self.arbiter.start_motion(knight, Position(0, 0), Position(2, 1))
        assert self.arbiter.advance_time(1000) == []
        assert self.arbiter.advance_time(1000) == []
        self.arbiter.start_motion(rook, Position(3, 0), Position(3, 1))

        events = self.arbiter.advance_time(1000)

        assert [event.piece.id for event in events] == [knight.id, rook.id]

    def test_multiple_waits_accumulate(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        for _ in range(9):
            assert self.arbiter.advance_time(100) == []

        events = self.arbiter.advance_time(100)

        assert len(events) == 1

    def test_tracks_two_pieces_independently(self) -> None:
        second_source = Position(2, 0)
        second_destination = Position(2, 2)
        second_piece = Piece("bR_2_0", "b", "R", second_source)

        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_motion(
            second_piece,
            second_source,
            second_destination,
        )

        assert self.arbiter.is_piece_busy("wR_0_0")
        assert self.arbiter.is_piece_busy("bR_2_0")
        assert not (self.arbiter.is_piece_busy("wK_1_1"))

    def test_rejects_second_motion_for_same_piece(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        with pytest.raises(ValueError, match="^piece_busy$"):
            self.arbiter.start_motion(
                self.piece,
                self.src,
                Position(0, 2),
            )

    def test_cancel_action_stops_motion_without_changing_piece_state(
        self,
    ) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.piece.state = "captured"

        self.arbiter.cancel_action(self.piece.id)

        assert not (self.arbiter.is_piece_busy(self.piece.id))
        assert self.arbiter.advance_time(1000) == []
        assert self.piece.state == "captured"

    def test_advance_time_returns_every_completed_motion(self) -> None:
        second_source = Position(2, 0)
        second_piece = Piece("bR_2_0", "b", "R", second_source)

        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_motion(
            second_piece,
            second_source,
            Position(2, 1),
        )

        events = self.arbiter.advance_time(1000)

        assert [event.piece.id for event in events] == ["wR_0_0", "bR_2_0"]
        # Still authoritative: neither completion has been resolved yet.
        assert len(self.arbiter.active_actions()) == 2

        self.arbiter.resolve_arrival(self.piece.id)
        self.arbiter.resolve_arrival(second_piece.id)

        assert self.arbiter.active_actions() == ()

    def test_active_actions_are_immutable_copies(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        actions = self.arbiter.active_actions()

        assert len(actions) == 1
        assert actions[0].piece_id == "wR_0_0"
        assert actions[0].piece_color == "w"
        assert not (hasattr(actions[0], "piece"))

        with pytest.raises(AttributeError):
            setattr(actions[0], "elapsed_ms", 500)  # noqa: B010

    def test_active_actions_include_moves_and_jumps(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_jump(jumper, landing)

        actions = self.arbiter.active_actions()

        assert {action.action_kind for action in actions} == {"move", "jump"}
        assert {action.piece_kind for action in actions} == {"R", "K"}
        assert all((not hasattr(action, "piece") for action in actions))

    def test_active_jump_can_be_found_by_landing_cell(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_jump(jumper, landing)

        jump = self.arbiter.active_jump_at(landing)

        assert jump is not None
        assert jump is not None
        assert jump.piece_id == "wK_1_1"

    def test_jump_completes_after_one_cell_duration(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_jump(jumper, landing)

        assert self.arbiter.advance_time(999) == []
        events = self.arbiter.advance_time(1)

        assert len(events) == 1
        assert events[0].action_kind == "jump"
        assert events[0].destination == landing
        assert self.arbiter.is_piece_busy("wK_1_1")

        self.arbiter.resolve_arrival("wK_1_1")

        assert not (self.arbiter.is_piece_busy("wK_1_1"))

    def test_move_completion_precedes_jump_at_same_time(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        source = Position(1, 2)
        mover = Piece("bR_1_2", "b", "R", source)

        self.arbiter.start_jump(jumper, landing)
        self.arbiter.start_motion(mover, source, landing)

        events = self.arbiter.advance_time(1000)

        assert [event.action_kind for event in events] == ["move", "jump"]

    def test_arrival_event_preserves_piece_identity(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        event = self.arbiter.advance_time(1000)[0]

        assert event.piece is self.piece
        assert event.piece.id == self.piece.id

    def test_motion_updates_piece_lifecycle(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        assert self.piece.state == "moving"
        assert self.arbiter.advance_time(999) == []
        assert self.piece.state == "moving"

        self.arbiter.advance_time(1)

        # Completion is detected but not yet finalized: state must not
        # flip until resolve_arrival runs, so an arrival GameEngine
        # cannot yet apply never shows a piece as idle prematurely.
        assert self.piece.state == "moving"

        self.arbiter.resolve_arrival(self.piece.id)

        assert self.piece.state == "idle"

    def test_jump_updates_piece_lifecycle(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)

        self.arbiter.start_jump(jumper, landing)
        assert jumper.state == "moving"

        self.arbiter.advance_time(1000)

        assert jumper.state == "moving"

        self.arbiter.resolve_arrival(jumper.id)

        assert jumper.state == "idle"

    def test_completion_does_not_revive_captured_piece(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.piece.state = "captured"

        self.arbiter.advance_time(1000)

        assert self.piece.state == "captured"

        self.arbiter.resolve_arrival(self.piece.id)

        assert self.piece.state == "captured"

    def test_advance_time_reports_leftover_time_past_arrival(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1500)

        assert len(events) == 1
        assert events[0].leftover_ms == 500

    def test_advance_time_reports_zero_leftover_at_exact_arrival(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1000)

        assert events[0].leftover_ms == 0

    def test_cooldown_ms_properties_expose_configured_durations(self) -> None:
        arbiter = RealTimeArbiter(short_cooldown_ms=1500, long_cooldown_ms=9000)

        assert arbiter.short_cooldown_ms == 1500
        assert arbiter.long_cooldown_ms == 9000

    def test_consume_completed_rest_piece_ids_reports_and_clears(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        assert self.arbiter.consume_completed_rest_piece_ids() == ()

        self.arbiter.advance_time(2000)

        assert self.arbiter.consume_completed_rest_piece_ids() == (self.piece.id,)
        assert self.arbiter.consume_completed_rest_piece_ids() == ()

    def test_next_boundary_ms_is_none_when_nothing_scheduled(self) -> None:
        assert self.arbiter.next_boundary_ms() is None

    def test_next_boundary_ms_reports_nearest_motion(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        assert self.arbiter.next_boundary_ms() == 1000

        self.arbiter.advance_time(400)

        assert self.arbiter.next_boundary_ms() == 600

    def test_next_boundary_ms_is_minimum_across_motions_and_rests(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")  # 2000ms remaining

        second_source = Position(2, 0)
        second_piece = Piece("bR_2_0", "b", "R", second_source)
        self.arbiter.start_motion(
            second_piece, second_source, Position(2, 1)
        )  # 1000ms remaining

        assert self.arbiter.next_boundary_ms() == 1000

    def test_next_boundary_ms_ignores_cancelled_actions(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.cancel_action(self.piece.id)

        assert self.arbiter.next_boundary_ms() is None


class TestRouteCalculation:
    """Verify pure route geometry without involving board legality."""

    @pytest.mark.parametrize(
        ("piece_kind", "source", "destination", "expected"),
        [
            (
                "B",
                Position(0, 0),
                Position(3, 3),
                (Position(1, 1), Position(2, 2), Position(3, 3)),
            ),
            (
                "Q",
                Position(0, 0),
                Position(3, 3),
                (Position(1, 1), Position(2, 2), Position(3, 3)),
            ),
            (
                "R",
                Position(2, 3),
                Position(2, 0),
                (Position(2, 2), Position(2, 1), Position(2, 0)),
            ),
        ],
        ids=["B", "Q", "R"],
    )
    def test_slider_route_contains_every_cell_through_destination(
        self,
        piece_kind: str,
        source: Position,
        destination: Position,
        expected: tuple[Position, ...],
    ) -> None:
        assert calculate_route(piece_kind, source, destination) == expected

    def test_king_and_single_step_pawn_routes_contain_only_destination(self) -> None:
        source = Position(4, 4)
        destination = Position(3, 4)

        assert calculate_route("K", source, destination) == (destination,)
        assert calculate_route("P", source, destination) == (destination,)

    def test_initial_pawn_double_step_contains_intermediate_cell(self) -> None:
        assert calculate_route("P", Position(6, 2), Position(4, 2)) == (
            Position(5, 2),
            Position(4, 2),
        )

    def test_knight_uses_two_cell_axis_first_with_direction_signs(self) -> None:
        assert calculate_route("N", Position(5, 5), Position(4, 3)) == (
            Position(5, 4),
            Position(5, 3),
            Position(4, 3),
        )


class TestRealTimeArbiterCooldown:
    """Verify per-piece rest scheduling, busy semantics, and time carry-over."""

    def setup_method(self) -> None:
        self.arbiter = RealTimeArbiter(short_cooldown_ms=2000, long_cooldown_ms=10000)
        self.piece = Piece("wP_1_0", "w", "P", Position(1, 0))

    def test_default_cooldown_durations_are_2000_and_10000(self) -> None:
        arbiter = RealTimeArbiter()
        arbiter.start_rest(self.piece, "short_rest")
        assert arbiter.active_rests()[0].duration_ms == DEFAULT_SHORT_COOLDOWN_MS

        other = Piece("wQ_0_0", "w", "Q", Position(0, 0))
        arbiter.start_rest(other, "long_rest")
        rests_by_id = {rest.piece_id: rest for rest in arbiter.active_rests()}
        assert rests_by_id["wQ_0_0"].duration_ms == DEFAULT_LONG_COOLDOWN_MS

    def test_start_rest_marks_piece_busy_and_sets_state(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        assert self.arbiter.is_piece_busy(self.piece.id)
        assert self.piece.state == "long_rest"

    def test_long_rest_completes_exactly_after_10000ms(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.advance_time(9999)
        assert self.piece.state == "long_rest"
        assert self.arbiter.is_piece_busy(self.piece.id)

        self.arbiter.advance_time(1)
        assert self.piece.state == "idle"
        assert not (self.arbiter.is_piece_busy(self.piece.id))

    def test_short_rest_completes_exactly_after_2000ms(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        self.arbiter.advance_time(1999)
        assert self.piece.state == "short_rest"

        self.arbiter.advance_time(1)
        assert self.piece.state == "idle"

    def test_partial_rest_remains_active(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.advance_time(4000)

        active = self.arbiter.active_rests()
        assert len(active) == 1
        assert active[0].elapsed_ms == 4000
        assert active[0].duration_ms == 10000

    def test_excessive_wait_returns_piece_to_idle(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        self.arbiter.advance_time(50000)

        assert self.piece.state == "idle"
        assert self.arbiter.active_rests() == ()

    def test_start_rest_with_zero_elapsed_begins_at_zero(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=0)

        active = self.arbiter.active_rests()
        assert active[0].elapsed_ms == 0
        assert self.piece.state == "long_rest"

    def test_start_rest_with_leftover_applies_remaining_time(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=4000)

        active = self.arbiter.active_rests()
        assert active[0].elapsed_ms == 4000
        assert self.piece.state == "long_rest"

    def test_start_rest_with_leftover_crossing_full_cooldown_ends_idle(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=10000)

        assert self.piece.state == "idle"
        assert self.arbiter.active_rests() == ()

    def test_cancel_action_removes_active_rest(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.cancel_action(self.piece.id)

        assert not (self.arbiter.is_piece_busy(self.piece.id))
        assert self.arbiter.active_rests() == ()

    def test_cancelled_rest_does_not_resurface_later(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")
        self.piece.state = "captured"

        self.arbiter.cancel_action(self.piece.id)
        self.arbiter.advance_time(50000)

        assert self.piece.state == "captured"

    def test_start_rest_rejects_already_busy_piece(self) -> None:
        self.arbiter.start_motion(self.piece, Position(1, 0), Position(1, 1))

        with pytest.raises(ValueError, match="^piece_busy$"):
            self.arbiter.start_rest(self.piece, "long_rest")

    def test_two_pieces_rest_concurrently_with_independent_elapsed_time(self) -> None:
        other = Piece("bP_6_0", "b", "P", Position(6, 0))
        self.arbiter.start_rest(self.piece, "long_rest")
        self.arbiter.start_rest(other, "short_rest")

        self.arbiter.advance_time(2000)

        assert other.state == "idle"
        assert self.piece.state == "long_rest"
        remaining = self.arbiter.active_rests()
        assert len(remaining) == 1
        assert remaining[0].piece_id == self.piece.id

    def test_one_piece_rests_while_another_moves(self) -> None:
        mover = Piece("bR_2_0", "b", "R", Position(2, 0))
        self.arbiter.start_rest(self.piece, "short_rest")
        self.arbiter.start_motion(mover, Position(2, 0), Position(2, 1))

        events = self.arbiter.advance_time(2000)

        assert len(events) == 1
        assert self.piece.state == "idle"
        assert self.arbiter.is_piece_busy(mover.id)

        self.arbiter.resolve_arrival(mover.id)

        assert not (self.arbiter.is_piece_busy(mover.id))


class TestArrivalResolutionProtocol:
    """Verify the two-phase completion protocol: advance_time only detects
    a completed motion; resolve_arrival is the sole step that finalizes it
    (removes it from scheduling and returns its piece to idle). A caller
    that never resolves a detected completion (because GameOver decided
    the outcome first) leaves the motion authoritative instead of losing
    track of its piece.
    """

    def setup_method(self) -> None:
        self.arbiter = RealTimeArbiter()
        self.src = Position(0, 0)
        self.dst = Position(0, 1)
        self.piece = Piece("wR_0_0", "w", "R", self.src)

    def test_completed_motion_stays_busy_until_resolved(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.arbiter.advance_time(1000)

        assert self.arbiter.is_piece_busy(self.piece.id)

    def test_completed_motion_stays_in_active_actions_until_resolved(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.arbiter.advance_time(1000)

        actions = self.arbiter.active_actions()
        assert len(actions) == 1
        assert actions[0].piece_id == "wR_0_0"

    def test_resolve_arrival_finalizes_motion_and_returns_piece_to_idle(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.advance_time(1000)

        self.arbiter.resolve_arrival(self.piece.id)

        assert not (self.arbiter.is_piece_busy(self.piece.id))
        assert self.arbiter.active_actions() == ()
        assert self.piece.state == "idle"

    def test_resolve_arrival_is_noop_for_incomplete_motion(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.advance_time(500)

        self.arbiter.resolve_arrival(self.piece.id)

        assert self.arbiter.is_piece_busy(self.piece.id)
        assert self.piece.state == "moving"

    def test_resolve_arrival_is_noop_for_unknown_piece_id(self) -> None:
        self.arbiter.resolve_arrival("no_such_piece")  # must not raise

    def test_completed_unresolved_motion_emits_its_arrival_exactly_once(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        first = self.arbiter.advance_time(1000)
        second = self.arbiter.advance_time(1)

        assert len(first) == 1
        assert first[0].piece.id == self.piece.id
        assert second == []

    def test_completed_unresolved_motion_elapsed_ms_does_not_grow_past_duration(
        self,
    ) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.arbiter.advance_time(1000)
        self.arbiter.advance_time(500)
        self.arbiter.advance_time(500)

        elapsed = self.arbiter.active_actions()[0].elapsed_ms
        assert elapsed == 1000

    def test_next_boundary_ms_ignores_completed_unresolved_motions(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)  # 1000ms

        self.arbiter.advance_time(1000)  # completes, left unresolved

        # Nothing else scheduled: the completed-but-inert motion must not
        # manufacture a zero-length boundary.
        assert self.arbiter.next_boundary_ms() is None

        other = Piece("bR_2_0", "b", "R", Position(2, 0))
        self.arbiter.start_motion(other, Position(2, 0), Position(2, 2))  # 2000ms

        # The still-pending motion's own remaining time is reported; the
        # completed-and-inert one is excluded, not treated as a 0 boundary.
        assert self.arbiter.next_boundary_ms() == 1000

    def test_completed_unresolved_motion_remains_observable_until_resolved(
        self,
    ) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.arbiter.advance_time(1000)
        self.arbiter.advance_time(1000)  # a later call must not disturb it

        assert self.arbiter.is_piece_busy(self.piece.id)
        assert len(self.arbiter.active_actions()) == 1
        assert self.piece.state == "moving"

        self.arbiter.resolve_arrival(self.piece.id)

        assert not (self.arbiter.is_piece_busy(self.piece.id))
        assert self.arbiter.active_actions() == ()
        assert self.piece.state == "idle"


class TestTimedRecordValidation:
    """Harden Motion and Rest, the lowest-level owners of timed records,
    against zero, negative, or boolean durations.
    """

    def setup_method(self) -> None:
        self.piece = Piece("wR_0_0", "w", "R", Position(0, 0))

    def test_zero_duration_motion_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Motion(
                piece=self.piece,
                action_kind="move",
                source=Position(0, 0),
                destination=Position(0, 0),
                duration_ms=0,
            )

    def test_negative_duration_motion_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Motion(
                piece=self.piece,
                action_kind="move",
                source=Position(0, 0),
                destination=Position(0, 1),
                duration_ms=-1000,
            )

    def test_boolean_duration_motion_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            Motion(
                piece=self.piece,
                action_kind="move",
                source=Position(0, 0),
                destination=Position(0, 1),
                duration_ms=True,
            )

    def test_positive_duration_motion_is_accepted(self) -> None:
        motion = Motion(
            piece=self.piece,
            action_kind="move",
            source=Position(0, 0),
            destination=Position(0, 1),
            duration_ms=1000,
        )
        assert motion.duration_ms == 1000

    def test_zero_duration_rest_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Rest(piece=self.piece, rest_kind="short_rest", duration_ms=0)

    def test_negative_duration_rest_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Rest(piece=self.piece, rest_kind="short_rest", duration_ms=-500)

    def test_boolean_duration_rest_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            Rest(piece=self.piece, rest_kind="short_rest", duration_ms=False)

    def test_positive_duration_rest_is_accepted(self) -> None:
        rest = Rest(piece=self.piece, rest_kind="long_rest", duration_ms=10000)
        assert rest.duration_ms == 10000

    def test_zero_cooldown_configured_arbiter_rejects_on_start_rest(self) -> None:
        arbiter = RealTimeArbiter(short_cooldown_ms=0)
        piece = Piece("wP_1_0", "w", "P", Position(1, 0))

        with pytest.raises(ValueError):
            arbiter.start_rest(piece, "short_rest")

    def test_next_boundary_ms_positive_for_valid_active_motion_and_rest(self) -> None:
        arbiter = RealTimeArbiter()
        mover = Piece("wR_0_0", "w", "R", Position(0, 0))
        rester = Piece("wN_1_0", "w", "N", Position(1, 0))

        arbiter.start_motion(mover, Position(0, 0), Position(0, 1))
        arbiter.start_rest(rester, "short_rest")

        boundary = arbiter.next_boundary_ms()
        assert boundary is not None
        assert boundary is not None
        assert boundary > 0
