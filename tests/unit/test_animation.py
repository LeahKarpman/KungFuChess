from __future__ import annotations

import pytest

from kungfu_chess.ui.animation import clamp_progress, lerp_point, select_frame_index


class TestClampProgress:
    def test_zero_elapsed_is_zero_progress(self) -> None:
        assert clamp_progress(0, 1000) == 0.0

    def test_half_elapsed_is_half_progress(self) -> None:
        assert clamp_progress(500, 1000) == 0.5

    def test_full_elapsed_is_full_progress(self) -> None:
        assert clamp_progress(1000, 1000) == 1.0

    def test_negative_elapsed_clamps_to_zero(self) -> None:
        assert clamp_progress(-500, 1000) == 0.0

    def test_excessive_elapsed_clamps_to_one(self) -> None:
        assert clamp_progress(5000, 1000) == 1.0

    def test_zero_duration_raises_clear_error(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            clamp_progress(0, 0)

    def test_negative_duration_raises_clear_error(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            clamp_progress(0, -1000)


class TestLerpPoint:
    def test_horizontal_interpolation(self) -> None:
        assert lerp_point((0.0, 50.0), (100.0, 50.0), 0.5) == (50.0, 50.0)

    def test_vertical_interpolation(self) -> None:
        assert lerp_point((50.0, 0.0), (50.0, 100.0), 0.25) == (50.0, 25.0)

    def test_diagonal_interpolation(self) -> None:
        assert lerp_point((0.0, 0.0), (100.0, 200.0), 0.5) == (50.0, 100.0)

    def test_zero_progress_returns_source_point(self) -> None:
        assert lerp_point((10.0, 20.0), (30.0, 40.0), 0.0) == (10.0, 20.0)

    def test_full_progress_returns_destination_point(self) -> None:
        assert lerp_point((10.0, 20.0), (30.0, 40.0), 1.0) == (30.0, 40.0)


class TestSelectFrameIndex:
    def test_first_frame_at_zero_elapsed(self) -> None:
        assert select_frame_index(0, 12, 5, is_loop=True) == 0

    def test_expected_frame_from_frames_per_sec(self) -> None:
        # 250ms at 12fps -> floor(0.25 * 12) = floor(3.0) = 3
        assert select_frame_index(250, 12, 5, is_loop=True) == 3

    def test_looping_animation_wraps(self) -> None:
        # 500ms at 12fps -> floor(6.0) = 6, wraps to 6 % 5 = 1
        assert select_frame_index(500, 12, 5, is_loop=True) == 1

    def test_non_looping_animation_holds_last_frame(self) -> None:
        # 5000ms at 8fps is far past frame_count=5, clamps to the last index
        assert select_frame_index(5000, 8, 5, is_loop=False) == 4

    def test_non_positive_frames_per_sec_raises_clear_error(self) -> None:
        with pytest.raises(ValueError, match="frames_per_sec"):
            select_frame_index(0, 0, 5, is_loop=True)

    @pytest.mark.parametrize("frame_count", [0, -1])
    def test_non_positive_frame_count_raises_clear_error(
        self, frame_count: int
    ) -> None:
        with pytest.raises(ValueError, match="frame_count"):
            select_frame_index(0, 12, frame_count, is_loop=True)
