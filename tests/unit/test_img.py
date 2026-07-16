from __future__ import annotations

import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
