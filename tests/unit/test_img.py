from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from kungfu_chess.ui.img import Img


class TestImgCopy(unittest.TestCase):
    def test_copy_creates_independent_pixel_data(self) -> None:
        original = Img()
        original.img = np.zeros((4, 4, 4), dtype=np.uint8)

        duplicate = original.copy()
        duplicate.img[0, 0, 0] = 255

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

    def test_close_all_windows_delegates_to_destroy_all_windows(self) -> None:
        with patch("kungfu_chess.ui.img.cv2") as mocked_cv2:
            Img.close_all_windows()

        mocked_cv2.destroyAllWindows.assert_called_once()


class TestImgMouseCallback(unittest.TestCase):
    """Verify left-click delegation without opening a real OpenCV window.

    namedWindow/setMouseCallback are mocked out so no real window is created,
    but the real cv2 event constants are used so the tests exercise the exact
    event codes OpenCV would deliver.
    """

    @staticmethod
    def _capture_on_mouse(mocked_set_mouse_callback) -> object:
        return mocked_set_mouse_callback.call_args.args[1]

    def test_left_button_down_invokes_public_callback_with_coordinates(self) -> None:
        callback = MagicMock()
        with patch("kungfu_chess.ui.img.cv2.namedWindow") as mocked_named_window, patch(
            "kungfu_chess.ui.img.cv2.setMouseCallback"
        ) as mocked_set_mouse_callback:
            Img.set_left_click_callback("Kung-Fu Chess", callback)
            mocked_named_window.assert_called_once_with("Kung-Fu Chess")
            on_mouse = self._capture_on_mouse(mocked_set_mouse_callback)

        on_mouse(cv2.EVENT_LBUTTONDOWN, 42, 84, 0, None)

        callback.assert_called_once_with(42, 84)

    def test_unrelated_mouse_events_do_not_invoke_public_callback(self) -> None:
        callback = MagicMock()
        with patch("kungfu_chess.ui.img.cv2.namedWindow"), patch(
            "kungfu_chess.ui.img.cv2.setMouseCallback"
        ) as mocked_set_mouse_callback:
            Img.set_left_click_callback("Kung-Fu Chess", callback)
            on_mouse = self._capture_on_mouse(mocked_set_mouse_callback)

        on_mouse(cv2.EVENT_MOUSEMOVE, 10, 20, 0, None)
        on_mouse(cv2.EVENT_RBUTTONDOWN, 10, 20, 0, None)
        on_mouse(cv2.EVENT_LBUTTONUP, 10, 20, 0, None)

        callback.assert_not_called()

    def test_public_callback_receives_only_x_and_y(self) -> None:
        """OpenCV event/flags/userdata details must not leak past Img."""
        callback = MagicMock()
        with patch("kungfu_chess.ui.img.cv2.namedWindow"), patch(
            "kungfu_chess.ui.img.cv2.setMouseCallback"
        ) as mocked_set_mouse_callback:
            Img.set_left_click_callback("Kung-Fu Chess", callback)
            on_mouse = self._capture_on_mouse(mocked_set_mouse_callback)

        on_mouse(cv2.EVENT_LBUTTONDOWN, 7, 9, 123, object())

        callback.assert_called_once_with(7, 9)


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
