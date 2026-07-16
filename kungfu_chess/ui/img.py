from __future__ import annotations

import pathlib
from typing import Callable

import cv2
import numpy as np

class Img:
    def __init__(self):
        self.img = None

    def read(self, path: str | pathlib.Path,
             size: tuple[int, int] | None = None,
             keep_aspect: bool = False,
             interpolation: int = cv2.INTER_AREA) -> "Img":
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
        self.img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
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

            self.img = cv2.resize(self.img, (new_w, new_h), interpolation=interpolation)

        return self

    def draw_on(self, other_img, x, y):
        if self.img is None or other_img.img is None:
            raise ValueError("Both images must be loaded before drawing.")

        if self.img.shape[2] != other_img.img.shape[2]:
            if self.img.shape[2] == 3 and other_img.img.shape[2] == 4:
                self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2BGRA)
            elif self.img.shape[2] == 4 and other_img.img.shape[2] == 3:
                self.img = cv2.cvtColor(self.img, cv2.COLOR_BGRA2BGR)

        h, w = self.img.shape[:2]
        H, W = other_img.img.shape[:2]

        if y + h > H or x + w > W:
            raise ValueError("Logo does not fit at the specified position.")

        roi = other_img.img[y:y + h, x:x + w]

        if self.img.shape[2] == 4:
            b, g, r, a = cv2.split(self.img)
            mask = a / 255.0
            for c in range(3):
                roi[..., c] = (1 - mask) * roi[..., c] + mask * self.img[..., c]
        else:
            other_img.img[y:y + h, x:x + w] = self.img

    def put_text(self, txt, x, y, font_size, color=(255, 255, 255, 255), thickness=1):
        if self.img is None:
            raise ValueError("Image not loaded.")
        cv2.putText(self.img, txt, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_size,
                    color, thickness, cv2.LINE_AA)

    def show(self):
        if self.img is None:
            raise ValueError("Image not loaded.")
        cv2.imshow("Image", self.img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def copy(self) -> "Img":
        """Return a new Img with an independent copy of the pixel data."""
        duplicate = Img()
        if self.img is not None:
            duplicate.img = self.img.copy()
        return duplicate

    def show_frame(self, window_name: str = "Image") -> None:
        """Display the current image without blocking and without closing the window."""
        if self.img is None:
            raise ValueError("Image not loaded.")
        cv2.imshow(window_name, self.img)

    @staticmethod
    def poll_key(delay_ms: int) -> int:
        """Process pending window events for delay_ms and return the pressed key code."""
        return cv2.waitKey(delay_ms) & 0xFF

    @staticmethod
    def close_all_windows() -> None:
        """Release every window opened by show() or show_frame()."""
        cv2.destroyAllWindows()

    @staticmethod
    def set_left_click_callback(
        window_name: str, callback: Callable[[int, int], None]
    ) -> None:
        """Invoke callback(x, y) once for every left-button press inside window_name.

        Creates the named window first if it does not exist yet, since OpenCV
        requires a window to exist before a mouse callback can be attached to it.
        All OpenCV mouse-event details (event codes, flags, userdata) stop here.
        """
        cv2.namedWindow(window_name)

        def _on_mouse(event: int, x: int, y: int, flags: int, userdata: object) -> None:
            if event == cv2.EVENT_LBUTTONDOWN:
                callback(x, y)

        cv2.setMouseCallback(window_name, _on_mouse)

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

        cv2.rectangle(self.img, top_left, bottom_right, color, thickness)
