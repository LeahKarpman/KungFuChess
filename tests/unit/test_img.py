from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np
import pytest

from kungfu_chess.ui.img import Img


class FakeCvWindowBackend:
    WND_PROP_VISIBLE = cv2.WND_PROP_VISIBLE
    EVENT_LBUTTONDOWN = cv2.EVENT_LBUTTONDOWN
    EVENT_RBUTTONDOWN = cv2.EVENT_RBUTTONDOWN
    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED
    COLOR_BGR2BGRA = cv2.COLOR_BGR2BGRA
    COLOR_BGRA2BGR = cv2.COLOR_BGRA2BGR
    FONT_HERSHEY_SIMPLEX = cv2.FONT_HERSHEY_SIMPLEX
    LINE_AA = cv2.LINE_AA
    error = cv2.error

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.key = -1
        self.image_to_read: np.ndarray | None = np.zeros((2, 3, 3), dtype=np.uint8)
        self.window_property = 1.0
        self.window_error: cv2.error | None = None
        self.mouse_callback: Callable[[int, int, int, int, object], None] | None = None

    def imshow(self, window_name: str, pixels: np.ndarray) -> None:
        self.calls.append(("imshow", window_name, pixels))

    def imread(self, path: str, mode: int) -> np.ndarray | None:
        self.calls.append(("imread", path, mode))
        if self.image_to_read is None:
            return None
        return self.image_to_read.copy()

    def resize(
        self,
        pixels: np.ndarray,
        size: tuple[int, int],
        *,
        interpolation: int,
    ) -> np.ndarray:
        self.calls.append(("resize", pixels, size, interpolation))
        width, height = size
        return np.zeros((height, width, pixels.shape[2]), dtype=pixels.dtype)

    def cvtColor(self, pixels: np.ndarray, conversion: int) -> np.ndarray:
        self.calls.append(("cvtColor", pixels, conversion))
        if conversion == self.COLOR_BGR2BGRA:
            alpha = np.full((*pixels.shape[:2], 1), 255, dtype=pixels.dtype)
            return np.concatenate((pixels, alpha), axis=2)
        if conversion == self.COLOR_BGRA2BGR:
            return pixels[:, :, :3].copy()
        raise AssertionError(f"Unexpected color conversion: {conversion}")

    def split(self, pixels: np.ndarray) -> tuple[np.ndarray, ...]:
        self.calls.append(("split", pixels))
        return tuple(pixels[:, :, index] for index in range(pixels.shape[2]))

    def putText(
        self,
        pixels: np.ndarray,
        text: str,
        origin: tuple[int, int],
        font: int,
        font_size: float,
        color: tuple[int, ...],
        thickness: int,
        line_type: int,
    ) -> None:
        self.calls.append(
            (
                "putText",
                pixels,
                text,
                origin,
                font,
                font_size,
                color,
                thickness,
                line_type,
            )
        )

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


class TestImgCreationAndLoading:
    def test_pixels_requires_a_loaded_image(self) -> None:
        with pytest.raises(ValueError, match="not loaded"):
            _ = Img().pixels

    @pytest.mark.parametrize(("width", "height"), [(0, 1), (1, 0), (-1, 1)])
    def test_create_rejects_non_positive_dimensions(
        self, width: int, height: int
    ) -> None:
        with pytest.raises(ValueError, match="dimensions"):
            Img().create(width, height)

    @pytest.mark.parametrize("color", [(), (1,), (1, 2), (1, 2, 3, 4, 5)])
    def test_create_rejects_unsupported_channel_counts(
        self, color: tuple[int, ...]
    ) -> None:
        with pytest.raises(ValueError, match="channels"):
            Img().create(2, 3, color)

    @pytest.mark.parametrize(
        "color",
        [(1, 2, 3), (1, 2, 3, 4)],
    )
    def test_create_returns_solid_pixels_with_requested_channels(
        self, color: tuple[int, ...]
    ) -> None:
        image = Img().create(2, 3, color)

        assert image.pixels.shape == (3, 2, len(color))
        assert tuple(image.pixels[0, 0]) == color

    def test_read_without_resize_preserves_loaded_dimensions(self) -> None:
        backend = FakeCvWindowBackend()
        backend.image_to_read = np.zeros((4, 6, 3), dtype=np.uint8)

        image = Img(backend).read("piece.png")

        assert image.pixels.shape == (4, 6, 3)
        assert [call[0] for call in backend.calls] == ["imread"]

    def test_read_resizes_to_exact_requested_dimensions(self) -> None:
        backend = FakeCvWindowBackend()
        backend.image_to_read = np.zeros((20, 40, 3), dtype=np.uint8)

        image = Img(backend).read("piece.png", size=(10, 10))

        assert image.pixels.shape == (10, 10, 3)
        assert backend.calls[-1][0] == "resize"
        assert backend.calls[-1][2] == (10, 10)

    def test_read_keep_aspect_fits_the_longer_side(self) -> None:
        backend = FakeCvWindowBackend()
        backend.image_to_read = np.zeros((20, 40, 3), dtype=np.uint8)

        image = Img(backend).read("piece.png", size=(10, 10), keep_aspect=True)

        assert image.pixels.shape == (5, 10, 3)
        assert backend.calls[-1][2] == (10, 5)

    def test_read_missing_file_raises_clear_error(self) -> None:
        backend = FakeCvWindowBackend()
        backend.image_to_read = None

        with pytest.raises(FileNotFoundError, match="missing.png"):
            Img(backend).read("missing.png")

    def test_resize_requires_loaded_pixels(self) -> None:
        with pytest.raises(ValueError, match="not loaded"):
            Img(FakeCvWindowBackend()).resize(10, 10)

    @pytest.mark.parametrize(("width", "height"), [(0, 10), (10, 0), (-1, 10)])
    def test_resize_rejects_non_positive_dimensions(
        self, width: int, height: int
    ) -> None:
        image = Img(FakeCvWindowBackend()).create(2, 2)

        with pytest.raises(ValueError, match="dimensions"):
            image.resize(width, height)

    def test_resize_delegates_to_the_explicit_backend(self) -> None:
        backend = FakeCvWindowBackend()
        image = Img(backend).create(2, 3, (1, 2, 3))

        result = image.resize(5, 7, interpolation=cv2.INTER_LINEAR)

        assert result is image
        assert image.pixels.shape == (7, 5, 3)
        assert backend.calls[-1][0] == "resize"
        assert backend.calls[-1][2:] == ((5, 7), cv2.INTER_LINEAR)


class TestImgComposition:
    @pytest.mark.parametrize(
        ("source_loaded", "target_loaded"),
        [(False, True), (True, False)],
    )
    def test_draw_on_requires_both_images_to_be_loaded(
        self, source_loaded: bool, target_loaded: bool
    ) -> None:
        source = Img(FakeCvWindowBackend())
        target = Img(FakeCvWindowBackend())
        if source_loaded:
            source.create(1, 1, (1, 2, 3))
        if target_loaded:
            target.create(2, 2, (1, 2, 3))

        with pytest.raises(ValueError, match="Both images"):
            source.draw_on(target, 0, 0)

    @pytest.mark.parametrize(
        ("source_shape", "target_shape", "message"),
        [
            ((1, 1), (1, 1, 3), "Source"),
            ((1, 1, 3), (1, 1), "Target"),
            ((1, 1, 2), (1, 1, 3), "Source"),
            ((1, 1, 3), (1, 1, 2), "Target"),
        ],
    )
    def test_draw_on_rejects_unsupported_pixel_shapes(
        self,
        source_shape: tuple[int, ...],
        target_shape: tuple[int, ...],
        message: str,
    ) -> None:
        source = Img(FakeCvWindowBackend())
        source.img = np.zeros(source_shape, dtype=np.uint8)
        target = Img(FakeCvWindowBackend())
        target.img = np.zeros(target_shape, dtype=np.uint8)

        with pytest.raises(ValueError, match=message):
            source.draw_on(target, 0, 0)

    def test_three_channel_source_is_converted_for_four_channel_target(self) -> None:
        backend = FakeCvWindowBackend()
        source = Img(backend).create(1, 1, (10, 20, 30))
        target = Img(backend).create(2, 2, (0, 0, 0, 0))

        source.draw_on(target, 0, 0)

        assert source.pixels.shape[2] == 4
        assert tuple(target.pixels[0, 0]) == (10, 20, 30, 0)
        assert any(call[0] == "cvtColor" for call in backend.calls)

    def test_four_channel_source_is_converted_for_three_channel_target(self) -> None:
        backend = FakeCvWindowBackend()
        source = Img(backend).create(1, 1, (10, 20, 30, 255))
        target = Img(backend).create(2, 2, (0, 0, 0))

        source.draw_on(target, 0, 0)

        assert source.pixels.shape[2] == 3
        assert tuple(target.pixels[0, 0]) == (10, 20, 30)

    def test_alpha_source_blends_into_target(self) -> None:
        backend = FakeCvWindowBackend()
        source = Img(backend).create(1, 1, (100, 50, 0, 255))
        target = Img(backend).create(2, 2, (0, 0, 0, 255))

        source.draw_on(target, 1, 1)

        assert tuple(target.pixels[1, 1, :3]) == (100, 50, 0)
        assert any(call[0] == "split" for call in backend.calls)

    def test_three_channel_source_copies_pixels_into_target(self) -> None:
        backend = FakeCvWindowBackend()
        source = Img(backend).create(1, 1, (10, 20, 30))
        target = Img(backend).create(2, 2, (0, 0, 0))

        source.draw_on(target, 1, 1)

        assert tuple(target.pixels[1, 1]) == (10, 20, 30)

    def test_draw_on_rejects_content_that_does_not_fit(self) -> None:
        backend = FakeCvWindowBackend()
        source = Img(backend).create(2, 2, (1, 2, 3))
        target = Img(backend).create(2, 2, (0, 0, 0))

        with pytest.raises(ValueError, match="does not fit"):
            source.draw_on(target, 1, 1)

    def test_put_text_requires_loaded_pixels(self) -> None:
        with pytest.raises(ValueError, match="not loaded"):
            Img(FakeCvWindowBackend()).put_text("Score", 1, 2, 0.5)

    def test_put_text_delegates_all_drawing_arguments(self) -> None:
        backend = FakeCvWindowBackend()
        image = Img(backend).create(10, 10)

        image.put_text("Score", 1, 2, 0.5, color=(4, 3, 2, 1), thickness=3)

        call = backend.calls[-1]
        assert call[0] == "putText"
        assert call[2:] == (
            "Score",
            (1, 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (4, 3, 2, 1),
            3,
            cv2.LINE_AA,
        )


class TestImgCopy:
    def test_copy_creates_independent_pixel_data(self) -> None:
        original = Img()
        original.img = np.zeros((4, 4, 4), dtype=np.uint8)

        duplicate = original.copy()
        duplicate.pixels[0, 0, 0] = 255

        assert original.img[0, 0, 0] == 0
        assert duplicate.img is not original.img

    def test_copy_of_unloaded_image_stays_unloaded(self) -> None:
        original = Img()
        duplicate = original.copy()
        assert duplicate.img is None


class TestImgWindowOperations:
    """Verify the persistent-window API without opening a real OpenCV window."""

    def test_show_frame_calls_imshow_without_blocking_or_closing(self) -> None:
        backend = FakeCvWindowBackend()
        img = Img(backend)
        img.img = np.zeros((2, 2, 3), dtype=np.uint8)

        img.show_frame("Kung-Fu Chess")

        assert len(backend.calls) == 1
        method, window_name, pixels = backend.calls[0]
        assert (method, window_name) == ('imshow', 'Kung-Fu Chess')
        assert pixels is img.img

    def test_show_frame_requires_loaded_image(self) -> None:
        img = Img()
        with pytest.raises(ValueError):
            img.show_frame("Kung-Fu Chess")

    def test_blocking_show_requires_loaded_image(self) -> None:
        with pytest.raises(ValueError, match="not loaded"):
            Img(FakeCvWindowBackend()).show()

    def test_blocking_show_displays_waits_and_closes(self) -> None:
        backend = FakeCvWindowBackend()
        image = Img(backend).create(2, 2, (1, 2, 3))

        image.show()

        assert [call[0] for call in backend.calls] == [
            "imshow",
            "waitKey",
            "destroyAllWindows",
        ]
        assert backend.calls[0][1] == "Image"
        assert backend.calls[1] == ("waitKey", 0)

    def test_poll_key_delegates_to_wait_key_with_delay(self) -> None:
        backend = FakeCvWindowBackend()
        backend.key = 27

        key = Img.poll_key(30, backend)

        assert backend.calls == [('waitKey', 30)]
        assert key == 27 & 255

    def test_is_window_open_returns_true_for_visible_window(self) -> None:
        backend = FakeCvWindowBackend()

        is_open = Img.is_window_open("Kung-Fu Chess", backend)

        assert backend.calls == [('getWindowProperty', 'Kung-Fu Chess', cv2.WND_PROP_VISIBLE)]
        assert is_open

    def test_is_window_open_returns_false_after_window_is_closed(self) -> None:
        backend = FakeCvWindowBackend()
        backend.window_property = -1.0

        is_open = Img.is_window_open("Kung-Fu Chess", backend)
        assert not is_open

    def test_is_window_open_returns_false_when_opencv_reports_missing_window(
        self,
    ) -> None:
        backend = FakeCvWindowBackend()
        backend.window_error = cv2.error("Window no longer exists")

        is_open = Img.is_window_open("Kung-Fu Chess", backend)
        assert not is_open

    def test_close_all_windows_delegates_to_destroy_all_windows(self) -> None:
        backend = FakeCvWindowBackend()

        Img.close_all_windows(backend)

        assert backend.calls == [('destroyAllWindows',)]


class TestImgMouseCallback:
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
        assert backend.mouse_callback is not None
        return backend, backend.mouse_callback

    def test_left_button_down_invokes_only_left_callback_with_coordinates(self) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        backend, on_mouse = self._install(on_left_click, on_right_click)
        assert backend.calls[0] == ('namedWindow', 'Kung-Fu Chess')

        on_mouse(cv2.EVENT_LBUTTONDOWN, 42, 84, 0, None)

        assert on_left_click.calls == [(42, 84)]
        assert on_right_click.calls == []

    def test_right_button_down_invokes_only_right_callback_with_coordinates(
        self,
    ) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_RBUTTONDOWN, 42, 84, 0, None)

        assert on_right_click.calls == [(42, 84)]
        assert on_left_click.calls == []

    def test_unrelated_mouse_events_invoke_neither_callback(self) -> None:
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_MOUSEMOVE, 10, 20, 0, None)
        on_mouse(cv2.EVENT_LBUTTONUP, 10, 20, 0, None)
        on_mouse(cv2.EVENT_RBUTTONUP, 10, 20, 0, None)

        assert on_left_click.calls == []
        assert on_right_click.calls == []

    def test_public_callbacks_receive_only_x_and_y(self) -> None:
        """OpenCV event/flags/userdata details must not leak past Img."""
        on_left_click = RecordingCallback()
        on_right_click = RecordingCallback()
        _, on_mouse = self._install(on_left_click, on_right_click)

        on_mouse(cv2.EVENT_LBUTTONDOWN, 7, 9, 123, object())
        on_mouse(cv2.EVENT_RBUTTONDOWN, 11, 13, 456, object())

        assert on_left_click.calls == [(7, 9)]
        assert on_right_click.calls == [(11, 13)]

    def test_exactly_one_mouse_callback_is_installed(self) -> None:
        backend, _ = self._install(RecordingCallback(), RecordingCallback())

        assert [call for call in backend.calls if call[0] == 'setMouseCallback'] == [('setMouseCallback', 'Kung-Fu Chess')]

    def test_named_window_created_before_callback_installed(self) -> None:
        backend = FakeCvWindowBackend()

        Img.set_mouse_callbacks(
            "Kung-Fu Chess", RecordingCallback(), RecordingCallback(), backend
        )

        assert [call[0] for call in backend.calls] == ['namedWindow', 'setMouseCallback']


class TestImgDrawRectangle:
    def test_draw_rectangle_changes_expected_border_pixels(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)

        img.draw_rectangle((2, 2), (10, 10), (255, 255, 255), 1)

        assert (img.img[2, 5] == 255).all()
        assert (img.img[5, 2] == 255).all()

    def test_pixels_outside_border_remain_unchanged(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)

        img.draw_rectangle((2, 2), (10, 10), (255, 255, 255), 1)

        assert (img.img[5, 5] == 0).all()  # inside the (unfilled) rectangle
        assert (img.img[0, 0] == 0).all()  # outside the rectangle entirely

    def test_draw_rectangle_on_unloaded_image_raises_clear_error(self) -> None:
        img = Img()
        with pytest.raises(ValueError, match='not loaded'):
            img.draw_rectangle((0, 0), (5, 5), (255, 255, 255), 1)

    def test_non_positive_thickness_raises_clear_error(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match='thickness'):
            img.draw_rectangle((0, 0), (5, 5), (255, 255, 255), 0)

    def test_degenerate_rectangle_coordinates_raise_clear_error(self) -> None:
        img = Img()
        img.img = np.zeros((20, 20, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match='bottom_right'):
            img.draw_rectangle((10, 10), (5, 5), (255, 255, 255), 1)
