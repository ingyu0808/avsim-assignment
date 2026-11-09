from types import SimpleNamespace

import numpy as np

from student_driver.perception import to_bgr


def test_to_bgr_swaps_channels_and_drops_row_padding():
    rgb = np.zeros((2, 3, 3), np.uint8)
    rgb[0, 0] = (255, 0, 0)
    padded = np.zeros((2, 3 * 3 + 7), np.uint8)
    padded[:, :9] = rgb.reshape(2, 9)
    msg = SimpleNamespace(height=2, width=3, step=16, data=padded.tobytes())
    bgr = to_bgr(msg)
    assert bgr.shape == (2, 3, 3)
    assert tuple(bgr[0, 0]) == (0, 0, 255)
