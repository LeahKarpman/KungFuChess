from __future__ import annotations

import pathlib
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np


class Img:
    def __init__(self, cv_backend: Any = cv2) -> None:
        self._cv = cv_backend
        self.img: np.ndarray | None = None

    @property
    def pixels(self) -> np.ndarray:
        """Return loaded pixel data, raising when the image has not been loaded."""
        if self.img is None:
            raise ValueError("Image not loaded.")
        return self.img

    def create(
        self,
        width: int,
        height: int,
        color: tuple[int, ...] = (0, 0, 0, 255),
    ) -> Img:
        """Create a solid-color image owned by this Img instance."""
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Image dimensions must be positive, got {width}x{height}."
            )
        if len(color) not in (3, 4):
            raise ValueError("Image color must have three or four channels.")
        self.img = np.full((height, width, len(color)), color, dtype=np.uint8)
        return self

    def read(
        self,
        path: str | pathlib.Path,
        size: tuple[int, int] | None = None,
        keep_aspect: bool = False,
        interpolation: int = cv2.INTER_AREA,
    ) -> Img:
        """
        Load `path` into self.img and **optionally resize**.

        Parameters
        ----------
        path : str | Path
            Image file to load.
        size : (width, height) | None
            Target size in pixels.  If None, keep original.
        keep_aspect : bool
            • False  → resize exactly to `size`
            • True   → shrink so the *longer* side fits `size` while
                       preserving aspect ratio (no cropping).
        interpolation : OpenCV flag
            E.g.  `cv2.INTER_AREA` for shrink, `cv2.INTER_LINEAR` for enlarge.

        Returns
        -------
        Img
            `self`, so you can chain:  `sprite = Img().read("foo.png", (64,64))`
        """
        path = str(path)
        self.img = self._cv.imread(path, self._cv.IMREAD_UNCHANGED)
        if self.img is None:
            raise FileNotFoundError(f"Cannot load image: {path}")

        if size is not None:
            target_w, target_h = size
            h, w = self.img.shape[:2]

            if keep_aspect:
                scale = min(target_w / w, target_h / h)
                new_w, new_h = int(w * scale), int(h * scale)
            else:
                new_w, new_h = target_w, target_h

            self.img = self._cv.resize(
                self.img, (new_w, new_h), interpolation=interpolation
            )

        return self

    def resize(
        self,
        width: int,
        height: int,
        interpolation: int = cv2.INTER_AREA,
    ) -> Img:
        """Resize loaded pixels while preserving their existing channel count."""
        if self.img is None:
            raise ValueError("Image not loaded.")
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Image dimensions must be positive, got {width}x{height}."
            )
        self.img = self._cv.resize(
            self.img,
            (width, height),
            interpolation=interpolation,
        )
        return self

    def draw_on(self, other_img, x, y):
        if self.img is None or other_img.img is None:
            raise ValueError("Both images must be loaded before drawing.")

        if self.img.shape[2] != other_img.img.shape[2]:
            if self.img.shape[2] == 3 and other_img.img.shape[2] == 4:
                self.img = self._cv.cvtColor(self.img, self._cv.COLOR_BGR2BGRA)
            elif self.img.shape[2] == 4 and other_img.img.shape[2] == 3:
                self.img = self._cv.cvtColor(self.img, self._cv.COLOR_BGRA2BGR)

        h, w = self.img.shape[:2]
        H, W = other_img.img.shape[:2]

        if y + h > H or x + w > W:
            raise ValueError("Logo does not fit at the specified position.")

        roi = other_img.img[y : y + h, x : x + w]

        if self.img.shape[2] == 4:
            a = self._cv.split(self.img)[3]
            mask = a / 255.0
            for c in range(3):
                roi[..., c] = (1 - mask) * roi[..., c] + mask * self.img[..., c]
        else:
            other_img.img[y : y + h, x : x + w] = self.img

    def put_text(self, txt, x, y, font_size, color=(255, 255, 255, 255), thickness=1):
        if self.img is None:
            raise ValueError("Image not loaded.")
        self._cv.putText(
            self.img,
            txt,
            (x, y),
            self._cv.FONT_HERSHEY_SIMPLEX,
            font_size,
            color,
            thickness,
            self._cv.LINE_AA,
        )

    def show(self):
        if self.img is None:
            raise ValueError("Image not loaded.")
        self._cv.imshow("Image", self.img)
        self._cv.waitKey(0)
        self._cv.destroyAllWindows()

    def copy(self) -> Img:
        """Return a new Img with an independent copy of the pixel data."""
        duplicate = Img(self._cv)
        if self.img is not None:
            duplicate.img = self.img.copy()
        return duplicate

    def show_frame(self, window_name: str = "Image") -> None:
        """Display the current image without blocking and without closing the window."""
        if self.img is None:
            raise ValueError("Image not loaded.")
        self._cv.imshow(window_name, self.img)

    @staticmethod
    def poll_key(delay_ms: int, cv_backend: Any = cv2) -> int:
        """Process pending window events for delay_ms and return the pressed key code."""
        return cv_backend.waitKey(delay_ms) & 0xFF

    @staticmethod
    def is_window_open(window_name: str, cv_backend: Any = cv2) -> bool:
        """Return whether window_name still has a visible OpenCV window."""
        try:
            return (
                cv_backend.getWindowProperty(
                    window_name, cv_backend.WND_PROP_VISIBLE
                )
                >= 1
            )
        except cv_backend.error:
            return False

    @staticmethod
    def close_all_windows(cv_backend: Any = cv2) -> None:
        """Release every window opened by show() or show_frame()."""
        cv_backend.destroyAllWindows()

    @staticmethod
    def set_mouse_callbacks(
        window_name: str,
        on_left_click: Callable[[int, int], object],
        on_right_click: Callable[[int, int], object],
        cv_backend: Any = cv2,
    ) -> None:
        """Invoke on_left_click(x, y) or on_right_click(x, y) for button presses inside window_name.

        Installs exactly one OpenCV mouse callback, since OpenCV supports only one
        callback per window, and dispatches it to the matching public callback.
        Creates the named window first if it does not exist yet, since OpenCV
        requires a window to exist before a mouse callback can be attached to it.
        All OpenCV mouse-event details (event codes, flags, userdata) stop here.
        """
        cv_backend.namedWindow(window_name)

        def _on_mouse(event: int, x: int, y: int, flags: int, userdata: object) -> None:
            if event == cv_backend.EVENT_LBUTTONDOWN:
                on_left_click(x, y)
            elif event == cv_backend.EVENT_RBUTTONDOWN:
                on_right_click(x, y)

        cv_backend.setMouseCallback(window_name, _on_mouse)

    def draw_rectangle(
        self,
        top_left: tuple[int, int],
        bottom_right: tuple[int, int],
        color: tuple[int, ...],
        thickness: int,
    ) -> None:
        """Draw an unfilled rectangle border directly onto this image."""
        if self.img is None:
            raise ValueError("Image not loaded.")
        if thickness <= 0:
            raise ValueError(f"Rectangle thickness must be positive, got {thickness}.")

        left, top = top_left
        right, bottom = bottom_right
        if right <= left or bottom <= top:
            raise ValueError(
                f"bottom_right {bottom_right} must be strictly greater than "
                f"top_left {top_left} in both dimensions."
            )

        self._cv.rectangle(self.img, top_left, bottom_right, color, thickness)
