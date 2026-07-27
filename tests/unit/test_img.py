from __future__ import annotations

import unittest
from collections.abc import Callable

import cv2
import numpy as np

from kungfu_chess.ui.img import Img


class FakeCvWindowBackend:
    WND_PROP_VISIBLE = cv2.WND_PROP_VISIBLE
    EVENT_LBUTTONDOWN = cv2.EVENT_LBUTTONDOWN
    EVENT_RBUTTONDOWN = cv2.EVENT_RBUTTONDOWN
    error = cv2.error

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.key = -1
        self.window_property = 1.0
        self.window_error: cv2.error | None = None
        self.mouse_callback: Callable[[int, int, int, int, object], None] | None = None

    def imshow(self, window_name: str, pixels: np.ndarray) -> None:
        self.calls.append(("imshow", window_name, pixels))

    def waitKey(self, delay_ms: int) -> int:
        self.calls.append(("waitKey", delay_ms))
        return self.key

    def destroyAllWindows(self) -> None:
        self.calls.append(("destroyAllWindows",))

    def getWindowProperty(self, window_name: str, property_id: int) -> float:
        self.calls.append(("getWindowProperty", window_name, property_id))
        if self.window_error is not None:
            raise self.window_error
        return self.window_property

    def namedWindow(self, window_name: str) -> None:
        self.calls.append(("namedWindow", window_name))

    def setMouseCallback(
        self,
        window_name: str,
        callback: Callable[[int, int, int, int, object], None],
    ) -> None:
        self.calls.append(("setMouseCallback", window_name))
        self.mouse_callback = callback


class RecordingCallback:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, x: int, y: int) -> None:
        self.calls.append((x, y))


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
        backend = FakeCvWindowBackend()
        img = Img(backend)
        img.img = np.zeros((2, 2, 3), dtype=np.uint8)

        img.show_frame("Kung-Fu Chess")

        self.assertEqual(len(backend.calls), 1)
        method, window_name, pixels = backend.calls[0]
        self.assertEqual((method, window_name), ("imshow", "Kung-Fu Chess"))
        self.assertIs(pixels, img.img)

    def test_show_frame_requires_loaded_image(self) -> None:
        img = Img()
        with self.assertRaises(ValueError):
            img.show_frame("Kung-Fu Chess")

    def test_poll_key_delegates_to_wait_key_with_delay(self) -> None:
        backend = FakeCvWindowBackend()
        backend.key = 27

        key = Img.poll_key(30, backend)

        self.assertEqual(backend.calls, [("waitKey", 30)])
        self.assertEqual(key, 27 & 0xFF)

    def test_is_window_open_returns_true_for_visible_window(self) -> None:
        backend = FakeCvWindowBackend()

        is_open = Img.is_window_open("Kung-Fu Chess", backend)

        self.assertEqual(
            backend.calls,
            [("getWindowProperty", "Kung-Fu Chess", cv2.WND_PROP_VISIBLE)],
        )
        self.assertTrue(is_open)

    def test_is_window_open_returns_false_after_window_is_closed(self) -> None:
        backend = FakeCvWindowBackend()
        backend.window_property = -1.0

        is_open = Img.is_window_open("Kung-Fu Chess", backend)
        self.assertFalse(is_open)

    def test_is_window_open_returns_false_when_opencv_reports_missing_window(
        self,
    ) -> None:
        backend = FakeCvWindowBackend()
        backend.window_error = cv2.error("Window no longer exists")

        is_open = Img.is_window_open("Kung-Fu Chess", backend)
        self.assertFalse(is_open)

    def test_close_all_windows_delegates_to_destroy_all_windows(self) -> None:
        backend = FakeCvWindowBackend()

        Img.close_all_windows(backend)

        self.assertEqual(backend.calls, [("destroyAllWindows",)])


class TestImgMouseCallback(unittest.TestCase):
    """Verify left/right-click dispatch without opening a real OpenCV window.

    A fake OpenCV backend prevents any real window from being created,
    but the real cv2 event constants are used so the tests exercise the exact
    event codes OpenCV would deliver.
    """

    def _install(self, on_left_click, on_right_click):
        backend = FakeCvWindowBackend()
        Img.set_mouse_callbacks(
            "Kung-Fu Chess", on_left_click, on_right_click, backend
        )
        self.assertIsNotNone(backend.mouse_callback)
        return backend, backend.mouse_callback

    def test_left_button_down_invokes_only_left_callback_with_coordinates(self) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        backend, on_mouse = self._install(on_left_click, on_right_click)
        self.assertEqual(backend.calls[0], ("namedWindow", "Kung-Fu Chess"))

        on_mouse(cv2.EVENT_LBUTTONDOWN, 42, 84, 0, None)

        self.assertEqual(on_left_click.calls, [(42, 84)])
        self.assertEqual(on_right_click.calls, [])

    def test_right_button_down_invokes_only_right_callback_with_coordinates(
        self,
    ) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_RBUTTONDOWN, 42, 84, 0, None)

        self.assertEqual(on_right_click.calls, [(42, 84)])
        self.assertEqual(on_left_click.calls, [])

    def test_unrelated_mouse_events_invoke_neither_callback(self) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_MOUSEMOVE, 10, 20, 0, None)
        on_mouse(cv2.EVENT_LBUTTONUP, 10, 20, 0, None)
        on_mouse(cv2.EVENT_RBUTTONUP, 10, 20, 0, None)

        self.assertEqual(on_left_click.calls, [])
        self.assertEqual(on_right_click.calls, [])

    def test_public_callbacks_receive_only_x_and_y(self) -> None:
        """OpenCV event/flags/userdata details must not leak past Img."""
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_LBUTTONDOWN, 7, 9, 123, object())
        on_mouse(cv2.EVENT_RBUTTONDOWN, 11, 13, 456, object())

        self.assertEqual(on_left_click.calls, [(7, 9)])
        self.assertEqual(on_right_click.calls, [(11, 13)])

    def test_exactly_one_mouse_callback_is_installed(self) -> None:
        backend, _ = self._install(RecordingCallback(), RecordingCallback())

        self.assertEqual(
            [call for call in backend.calls if call[0] == "setMouseCallback"],
            [("setMouseCallback", "Kung-Fu Chess")],
        )

    def test_named_window_created_before_callback_installed(self) -> None:
        backend = FakeCvWindowBackend()

        Img.set_mouse_callbacks(
            "Kung-Fu Chess", RecordingCallback(), RecordingCallback(), backend
        )

        self.assertEqual(
            [call[0] for call in backend.calls],
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
