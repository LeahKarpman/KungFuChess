from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import cast
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from kungfu_chess.ui.img import Img


class TestImgCopy(unittest.TestCase):
    def test_copy_creates_independent_pixel_data(self) -> None:
        original = Img()
        original.img = np.zeros((4, 4, 4), dtype=np.uint8)

        duplicate = original.copy()
        duplicate.pixels[0, 0, 0] = 255

        self.assertEqual(original.img[0, 0, 0], 0)
        self.assertIsNot(duplicate.img, original.img)

    def test_copy_of_unloaded_image_stays_unloaded(self) -> None:
        original = Img()
        duplicate = original.copy()
        self.assertIsNone(duplicate.img)


class TestImgWindowOperations(unittest.TestCase):
    """Verify the persistent-window API without opening a real OpenCV window."""

    def test_show_frame_calls_imshow_without_blocking_or_closing(self) -> None:
        img = Img()
        img.img = np.zeros((2, 2, 3), dtype=np.uint8)

        with patch("kungfu_chess.ui.img.cv2") as mocked_cv2:
            img.show_frame("Kung-Fu Chess")

        call_args = mocked_cv2.imshow.call_args
        self.assertEqual(call_args.args[0], "Kung-Fu Chess")
        self.assertIs(call_args.args[1], img.img)
        mocked_cv2.waitKey.assert_not_called()
        mocked_cv2.destroyAllWindows.assert_not_called()

    def test_show_frame_requires_loaded_image(self) -> None:
        img = Img()
        with self.assertRaises(ValueError):
            img.show_frame("Kung-Fu Chess")

    def test_poll_key_delegates_to_wait_key_with_delay(self) -> None:
        with patch("kungfu_chess.ui.img.cv2") as mocked_cv2:
            mocked_cv2.waitKey.return_value = 27
            key = Img.poll_key(30)

        mocked_cv2.waitKey.assert_called_once_with(30)
        self.assertEqual(key, 27 & 0xFF)

    def test_is_window_open_returns_true_for_visible_window(self) -> None:
        with patch(
            "kungfu_chess.ui.img.cv2.getWindowProperty", return_value=1.0
        ) as mocked_get_window_property:
            is_open = Img.is_window_open("Kung-Fu Chess")

        mocked_get_window_property.assert_called_once_with(
            "Kung-Fu Chess", cv2.WND_PROP_VISIBLE
        )
        self.assertTrue(is_open)

    def test_is_window_open_returns_false_after_window_is_closed(self) -> None:
        with patch("kungfu_chess.ui.img.cv2.getWindowProperty", return_value=-1.0):
            is_open = Img.is_window_open("Kung-Fu Chess")

        self.assertFalse(is_open)

    def test_is_window_open_returns_false_when_opencv_reports_missing_window(
        self,
    ) -> None:
        with patch(
            "kungfu_chess.ui.img.cv2.getWindowProperty",
            side_effect=cv2.error("Window no longer exists"),
        ):
            is_open = Img.is_window_open("Kung-Fu Chess")

        self.assertFalse(is_open)

    def test_close_all_windows_delegates_to_destroy_all_windows(self) -> None:
        with patch("kungfu_chess.ui.img.cv2") as mocked_cv2:
            Img.close_all_windows()

        mocked_cv2.destroyAllWindows.assert_called_once()


class TestImgMouseCallback(unittest.TestCase):
    """Verify left/right-click dispatch without opening a real OpenCV window.

    namedWindow/setMouseCallback are mocked out so no real window is created,
    but the real cv2 event constants are used so the tests exercise the exact
    event codes OpenCV would deliver.
    """

    @staticmethod
    def _capture_on_mouse(
        mocked_set_mouse_callback,
    ) -> Callable[[int, int, int, int, object], None]:
        return cast(
            Callable[[int, int, int, int, object], None],
            mocked_set_mouse_callback.call_args.args[1],
        )

    def _install(self, on_left_click, on_right_click):
        with (
            patch("kungfu_chess.ui.img.cv2.namedWindow") as mocked_named_window,
            patch(
                "kungfu_chess.ui.img.cv2.setMouseCallback"
            ) as mocked_set_mouse_callback,
        ):
            Img.set_mouse_callbacks("Kung-Fu Chess", on_left_click, on_right_click)
            on_mouse = self._capture_on_mouse(mocked_set_mouse_callback)
        return mocked_named_window, mocked_set_mouse_callback, on_mouse

    def test_left_button_down_invokes_only_left_callback_with_coordinates(self) -> None:
        on_left_click = MagicMock()
        on_right_click = MagicMock()
        mocked_named_window, _, on_mouse = self._install(on_left_click, on_right_click)
        mocked_named_window.assert_called_once_with("Kung-Fu Chess")

        on_mouse(cv2.EVENT_LBUTTONDOWN, 42, 84, 0, None)

        on_left_click.assert_called_once_with(42, 84)
        on_right_click.assert_not_called()

    def test_right_button_down_invokes_only_right_callback_with_coordinates(
        self,
    ) -> None:
        on_left_click = MagicMock()
        on_right_click = MagicMock()
        _, _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_RBUTTONDOWN, 42, 84, 0, None)

        on_right_click.assert_called_once_with(42, 84)
        on_left_click.assert_not_called()

    def test_unrelated_mouse_events_invoke_neither_callback(self) -> None:
        on_left_click = MagicMock()
        on_right_click = MagicMock()
        _, _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_MOUSEMOVE, 10, 20, 0, None)
        on_mouse(cv2.EVENT_LBUTTONUP, 10, 20, 0, None)
        on_mouse(cv2.EVENT_RBUTTONUP, 10, 20, 0, None)

        on_left_click.assert_not_called()
        on_right_click.assert_not_called()

    def test_public_callbacks_receive_only_x_and_y(self) -> None:
        """OpenCV event/flags/userdata details must not leak past Img."""
        on_left_click = MagicMock()
        on_right_click = MagicMock()
        _, _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_LBUTTONDOWN, 7, 9, 123, object())
        on_mouse(cv2.EVENT_RBUTTONDOWN, 11, 13, 456, object())

        on_left_click.assert_called_once_with(7, 9)
        on_right_click.assert_called_once_with(11, 13)

    def test_exactly_one_mouse_callback_is_installed(self) -> None:
        _, mocked_set_mouse_callback, _ = self._install(MagicMock(), MagicMock())

        self.assertEqual(mocked_set_mouse_callback.call_count, 1)

    def test_named_window_created_before_callback_installed(self) -> None:
        with patch("kungfu_chess.ui.img.cv2") as mocked_cv2:
            Img.set_mouse_callbacks("Kung-Fu Chess", MagicMock(), MagicMock())

        self.assertEqual(
            [call[0] for call in mocked_cv2.method_calls],
            ["namedWindow", "setMouseCallback"],
        )


class TestImgDrawRectangle(unittest.TestCase):
    def test_draw_rectangle_changes_expected_border_pixels(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)

        img.draw_rectangle((2, 2), (10, 10), (255, 255, 255), 1)

        self.assertTrue((img.img[2, 5] == 255).all())
        self.assertTrue((img.img[5, 2] == 255).all())

    def test_pixels_outside_border_remain_unchanged(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)

        img.draw_rectangle((2, 2), (10, 10), (255, 255, 255), 1)

        self.assertTrue((img.img[5, 5] == 0).all())  # inside the (unfilled) rectangle
        self.assertTrue((img.img[0, 0] == 0).all())  # outside the rectangle entirely

    def test_draw_rectangle_on_unloaded_image_raises_clear_error(self) -> None:
        img = Img()
        with self.assertRaisesRegex(ValueError, "not loaded"):
            img.draw_rectangle((0, 0), (5, 5), (255, 255, 255), 1)

    def test_non_positive_thickness_raises_clear_error(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "thickness"):
            img.draw_rectangle((0, 0), (5, 5), (255, 255, 255), 0)

    def test_degenerate_rectangle_coordinates_raise_clear_error(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "bottom_right"):
            img.draw_rectangle((10, 10), (5, 5), (255, 255, 255), 1)


if __name__ == "__main__":
    unittest.main()
