from kungfu_chess.model.position import Position


class TestPosition:
    def test_equality(self):
        assert Position(1, 2) == Position(1, 2)

    def test_inequality(self):
        assert Position(1, 2) != Position(2, 1)

    def test_repr(self):
        assert repr(Position(3, 4)) == "Position(3, 4)"

    def test_hashable(self):
        s = {Position(0, 0), Position(0, 0)}
        assert len(s) == 1
