"""Offline tests for the vision code using synthetic camera frames.
Run:  python -m unittest test_vision -v"""
import socket
import unittest

import cv2
import numpy as np

from vision_server import PACKET, centre_marker, make_detector


def synthetic_frame(markers, w=640, h=480, side=120, blur=1, noise=6, seed=0):
    """markers: list of (id, centre_x) placed on the horizontal mid-line."""
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img = np.full((h, w), 200, np.uint8)                       # grey-ish card/table
    for mid, cx in markers:
        m = cv2.aruco.generateImageMarker(d, mid, side)
        q = side // 6                                          # white quiet zone
        m = cv2.copyMakeBorder(m, q, q, q, q, cv2.BORDER_CONSTANT, value=255)
        s = m.shape[0]
        x, y = int(cx - s / 2), int(h / 2 - s / 2)
        xa, xb = max(x, 0), min(x + s, w)
        img[y:y + s, xa:xb] = m[:, xa - x:xb - x]
    if blur:
        img = cv2.GaussianBlur(img, (2 * blur + 1, 2 * blur + 1), 0)
    rng = np.random.default_rng(seed)
    img = np.clip(img + rng.normal(0, noise, img.shape), 0, 255).astype(np.uint8)
    return img


class TestVision(unittest.TestCase):
    def setUp(self):
        self.detect = make_detector()

    def test_reads_each_game_id(self):
        for mid in (0, 1, 2, 3, 4):
            g = synthetic_frame([(mid, 330)])
            r = centre_marker(*self.detect(g), g.shape)
            self.assertEqual(r[0], mid)
            self.assertEqual(r[2], 1)
            self.assertLess(abs(r[1] - 10), 3)

    def test_picks_centre_card_when_neighbour_in_view(self):
        g = synthetic_frame([(1, 90), (2, 320), (0, 560)])
        mid, off, valid, _ = centre_marker(*self.detect(g), g.shape)
        self.assertEqual((mid, valid), (2, 1))

    def test_off_centre_card_is_not_valid(self):
        g = synthetic_frame([(1, 480)])
        mid, off, valid, _ = centre_marker(*self.detect(g), g.shape, center_tol_px=60)
        self.assertEqual(mid, 1)
        self.assertEqual(valid, 0)

    def test_no_marker(self):
        g = synthetic_frame([])
        self.assertEqual(centre_marker(*self.detect(g), g.shape)[:3], (-1, 0, 0))

    def test_repeatability_with_noise(self):
        ok = 0
        for seed in range(50):
            g = synthetic_frame([(seed % 3, 320)], noise=12, blur=2, seed=seed)
            ok += centre_marker(*self.detect(g), g.shape)[0] == seed % 3
        self.assertGreaterEqual(ok, 49)

    def test_packet_over_udp(self):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.settimeout(1)
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tx.sendto(PACKET.pack(7, 2, -13, 1), rx.getsockname())
        data, _ = rx.recvfrom(64)
        self.assertEqual(len(data), 16)                 # Simulink: int32, size 4
        self.assertEqual(PACKET.unpack(data), (7, 2, -13, 1))
        rx.close()
        tx.close()


if __name__ == "__main__":
    unittest.main()
