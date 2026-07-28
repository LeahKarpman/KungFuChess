# pyright: reportOptionalMemberAccess=false

from kungfu_chess.model.position import Position
from tests.unit.game_engine_test_support import make_engine as _engine


class TestGameOver:
    """Verify king capture makes the engine reject later moves."""

    def test_king_capture_sets_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )

        engine.wait(2000)

        assert engine.game_over

    def test_game_over_blocks_further_moves(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )
        engine.wait(2000)

        result = engine.request_move(
            Position(0, 2),
            Position(0, 0),
        )

        assert result.reason == "game_over"


class TestCooldownGameOver:
    def test_capturing_a_king_ends_the_game(self) -> None:
        engine, _board = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        assert engine.game_over

    def test_surviving_capturing_piece_receives_no_rest_record_after_game_over(self) -> None:
        engine, board = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        survivor = board.get_piece(Position(0, 2))
        assert survivor.state == "idle"
        assert engine.snapshot().rests == ()

    def test_jump_capture_of_king_grants_no_rest_to_jumper(self) -> None:
        engine, board = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))

        engine.wait(1000)

        winner = board.get_piece(Position(1, 0))
        assert engine.game_over
        assert winner.state == "idle"
        assert engine.snapshot().rests == ()


class TestGameOverHardening:
    """Verify that game over is terminal: simulated time stops the instant
    a king is captured, no completed-but-unresolved action orphans its
    piece, and the terminal snapshot never drifts afterward.
    """

    def test_wait_after_game_over_does_not_change_snapshot(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        assert engine.game_over
        before = engine.snapshot()

        engine.wait(5000)

        assert engine.snapshot() == before

    def test_wait_after_game_over_emits_no_events(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        engine.consume_events()

        engine.wait(5000)

        assert engine.consume_events() == ()

    def test_repeated_waits_after_game_over_remain_no_ops(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        engine.consume_events()
        before = engine.snapshot()

        for _ in range(3):
            engine.wait(1000)
            assert engine.snapshot() == before
            assert engine.consume_events() == ()

    def test_large_wait_stops_at_boundary_unused_motion_time_is_discarded(self) -> None:
        """A single wait() spanning well past the king capture must not let
        its leftover milliseconds keep advancing an unrelated in-flight
        motion, even though the same call had more than enough time to
        finish it.
        """
        engine, board = _engine(["bK wR . . . wN", ". . . . . ."])
        engine.request_move(Position(0, 5), Position(1, 3))  # knight, 3000ms
        engine.request_move(Position(0, 1), Position(0, 0))  # rook captures king, 1000ms
        engine.consume_events()

        engine.wait(10000)

        assert engine.game_over
        assert board.get_piece(Position(1, 3)) is None
        # The knight advanced to its first visual waypoint at the same
        # millisecond, but its authoritative occupied cell remains its source.
        knight = board.get_piece(Position(0, 5))
        assert knight is not None
        assert knight.state == "moving"

        motions = {m.piece_id: m for m in engine.snapshot().motions}
        assert knight.id in motions
        assert motions[knight.id].source == Position(0, 5)
        assert motions[knight.id].destination == Position(1, 3)
        assert motions[knight.id].elapsed_ms == 1000
        assert motions[knight.id].duration_ms == 3000
        assert motions[knight.id].action_elapsed_ms == 1000

    def test_large_wait_stops_at_boundary_unused_rest_time_is_discarded(self) -> None:
        """Same guarantee for an already-active rest: its cooldown must not
        keep advancing past the boundary where the game ends, even though
        the wait() call had more than enough leftover time to finish it.
        """
        engine, board = _engine(["wR . bK", "wR . ."])
        engine.request_move(Position(1, 0), Position(1, 1))
        engine.wait(1000)  # second rook arrives and starts its long_rest (10000ms)
        engine.consume_events()

        engine.request_move(Position(0, 0), Position(0, 2))  # captures king in 2000ms

        engine.wait(20000)

        assert engine.game_over
        rests = {r.piece_id: r for r in engine.snapshot().rests}
        assert "wR_1_0" in rests
        assert rests["wR_1_0"].elapsed_ms == 2000
        assert board.get_piece(Position(1, 1)).state == "long_rest"

    def test_jumping_piece_remains_represented_when_game_ends_first(self) -> None:
        """A move captures a king and a jump completes at the same boundary
        (move outranks jump in the tie order). The jump must not land —
        but the jumping piece must not vanish either: it stays represented
        by its now-authoritative, unresolved motion.
        """
        engine, board = _engine([". bK .", ". wR wN"])
        jumper = board.get_piece(Position(1, 2))

        engine.request_move(Position(1, 1), Position(0, 1))  # captures king, 1000ms
        engine.jump(Position(1, 2))  # uncontested, 1000ms
        engine.consume_events()

        engine.wait(1000)

        assert engine.game_over
        assert board.get_piece(Position(0, 1)).color == "w"
        assert board.get_piece(Position(1, 2)) is None

        assert jumper.state == "moving"
        assert jumper.state != "captured"

        snapshot = engine.snapshot()
        assert jumper.id in {p.id for p in snapshot.pieces}
        assert jumper.id in {m.piece_id for m in snapshot.motions}

    def test_jump_does_not_capture_second_king_after_move_ends_game(self) -> None:
        """A jump whose landing cell would hold a second king (because that
        king moved onto the jumper's vacated cell earlier in the same
        boundary batch) must not capture it once an unrelated move has
        already ended the game. The second king survives, the jumper
        remains represented, and an unrelated in-flight piece is also
        left untouched rather than silently dropped.
        """
        engine, board = _engine(
            [
                "bK wR . .",
                "wR . . .",
                "wP bK . .",
            ]
        )
        jumper = board.get_piece(Position(2, 0))
        second_king = board.get_piece(Position(2, 1))
        bystander = board.get_piece(Position(1, 0))

        engine.jump(Position(2, 0))  # sequence 0
        engine.request_move(Position(2, 1), Position(2, 0))  # sequence 1, fills vacated cell
        engine.request_move(Position(0, 1), Position(0, 0))  # sequence 2, captures first king
        engine.request_move(Position(1, 0), Position(1, 1))  # sequence 3, unrelated bystander move
        engine.consume_events()

        engine.wait(1000)

        assert engine.game_over
        assert board.get_piece(Position(0, 0)).color == "w"

        # Second king: landed successfully (its own move resolved before
        # the game ended) but was never captured by the blocked jump.
        assert board.get_piece(Position(2, 0)) is second_king
        assert second_king.state != "captured"

        # The jumper itself: never landed, never orphaned.
        assert jumper.id not in {p.id for p in board.all_pieces()}
        assert jumper.state == "moving"

        # The unrelated bystander's move was also blocked (later in the
        # same completion batch) and must not have vanished either.
        assert board.get_piece(Position(1, 0)) is bystander
        assert bystander.state == "moving"
        assert board.get_piece(Position(1, 1)) is None

        snapshot = engine.snapshot()
        ids = [p.id for p in snapshot.pieces]
        assert len(ids) == len(set(ids)), "no piece should be represented twice"
        assert jumper.id in ids
        assert bystander.id in ids

    def test_repeated_snapshots_after_game_over_are_equal(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        assert engine.snapshot() == engine.snapshot()

    def test_no_captured_piece_returns_after_later_wait(self) -> None:
        engine, board = _engine(["wR . bK"])
        king = board.get_piece(Position(0, 2))
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        assert king.state == "captured"

        engine.wait(5000)

        assert king.state == "captured"
        assert board.get_piece(Position(0, 2)).color == "w"
