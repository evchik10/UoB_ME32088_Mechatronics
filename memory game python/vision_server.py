"""
ArUco vision server for the gantry memory game - calibrated version.

Based on the team's camera template: uses the camera calibration
(workdir/Calibration.npz -> CM, dist_coef) and solvePnP to measure where each
marker is in millimetres relative to the camera. The marker closest to the
camera centre along the gantry axis is "the card under the carriage"; its ID
is sent to Simulink over UDP once per processed frame.

UDP packet (unchanged, so the Simulink model needs no change):
    4 x int32, little-endian:  [seq, marker_id, offset_01mm, valid]
      seq          +1 every processed frame (Simulink waits for it to rise)
      marker_id    ArUco ID of the centre marker, -1 if none
      offset_01mm  marker centre minus camera centre along the gantry axis,
                   in 0.1 mm (e.g. 123 = 12.3 mm). Simulink ignores it for now;
                   useful for logging or a fine-positioning upgrade later.
      valid        1 if that marker is within --tol-mm of the camera centre

Usage:
    python3 vision_server.py --print                 # on the Pi, headless
    python3 vision_server.py --show --print          # with the two preview windows
    python3 vision_server.py --camera 1 --backend msmf --show   # Windows laptop, USB cam
"""
from __future__ import annotations

import argparse
import logging
import socket
import struct
import sys
import time
from pathlib import Path

import cv2
import cv2.aruco as aruco
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("vision")

PACKET = struct.Struct("<4i")       # Simulink UDP Receive: int32, size 4


# --------------------------------------------------------------------------
# Setup helpers
# --------------------------------------------------------------------------
def load_calibration(path: Path):
    """Load the camera matrix CM and distortion coefficients from the .npz file
    produced by the calibration script. Calibration is only valid at the image
    resolution it was made at - capture at that same resolution."""
    if not path.exists():
        log.error("Calibration file not found: %s", path)
        raise SystemExit(1)
    cal = np.load(path)
    log.info("Loaded camera calibration from %s", path.name)
    return cal["CM"], cal["dist_coef"]


def make_detector():
    """ArUco detector for DICT_4X4_50 (OpenCV 4.7+ / 5 API, as in the template)."""
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    params = aruco.DetectorParameters()
    params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX   # more accurate corners -> better pose
    return aruco.ArucoDetector(aruco_dict, params)


def marker_object_points(marker_mm: float) -> np.ndarray:
    """3D corners of a marker in its own frame (origin at the centre, mm).
    Order matches the detector: top-left, top-right, bottom-right, bottom-left."""
    h = marker_mm / 2
    return np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], dtype=np.float32)


def open_camera(index: int, backend: str, width: int, height: int):
    """Open the USB camera. 'auto' picks V4L2 on Linux (Pi) and MSMF on Windows."""
    if backend == "auto":
        backend = "msmf" if sys.platform.startswith("win") else "v4l2"
    api = {"v4l2": cv2.CAP_V4L2, "msmf": cv2.CAP_MSMF, "dshow": cv2.CAP_DSHOW,
           "any": cv2.CAP_ANY}[backend]
    cap = cv2.VideoCapture(index, api)
    if not cap.isOpened():
        log.error("Could not open camera %d (backend %s)", index, backend)
        raise SystemExit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, heigfffht)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)            # always process the newest frame
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info("Camera %d opened at %dx%d (%s)", index, w, h, backend)
    return cap


# --------------------------------------------------------------------------
# Core: which card is under the camera?
# --------------------------------------------------------------------------
def measure_markers(corners, ids, obj_pts, CM, dist_coef):
    """Pose of every detected marker. Returns a list of (id, x_mm, y_mm, z_mm, rvec, tvec).
    x/y = marker centre relative to the camera's optical axis, z = distance."""
    out = []
    if ids is None or len(corners) == 0:            # OpenCV 4: None, OpenCV 5: empty
        return out
    for c, marker_id in zip(corners, ids.flatten()):
        ok, rvec, tvec = cv2.solvePnP(obj_pts, c, CM, dist_coef, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if ok:
            x, y, z = (float(v) for v in tvec.ravel())
            out.append((int(marker_id), x, y, z, rvec, tvec))
    return out


def pick_centre_marker(poses, axis="x", sign=1, tol_mm=15.0):
    """Choose the marker nearest the camera centre along the gantry axis.
    Returns (marker_id, offset_mm, valid). offset is signed so that + means
    'further from home' when --sign is set correctly."""
    if not poses:
        return -1, 0.0, 0
    k = 1 if axis == "x" else 2                     # index into (id, x, y, z, ...)
    best = min(poses, key=lambda p: abs(p[k]))
    offset = sign * best[k]
    return best[0], offset, int(abs(offset) <= tol_mm)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calib", type=Path,
                    default=Path(__file__).resolve().parent / "workdir" / "Calibration.npz")
    ap.add_argument("--marker-mm", type=float, default=40.0,
                    help="printed black-square size in mm (must match your cards)")
    ap.add_argument("--camera", type=int, default=0, help="0 on the Pi; 1 for a USB cam on a laptop")
    ap.add_argument("--backend", choices=["auto", "v4l2", "msmf", "dshow", "any"], default="auto")
    ap.add_argument("--width", type=int, default=640, help="must match the calibration resolution")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--period", type=float, default=0.1,
                    help="seconds per processed frame (0.1 = 10 fps; template used 0.25)")
    ap.add_argument("--host", default="127.0.0.1", help="where Simulink runs (same Pi = 127.0.0.1)")
    ap.add_argument("--port", type=int, default=25000)
    ap.add_argument("--axis", choices=["x", "y"], default="x", help="camera axis along the gantry")
    ap.add_argument("--sign", type=int, choices=[1, -1], default=1,
                    help="-1 if offset is negative when the card is further from home")
    ap.add_argument("--tol-mm", type=float, default=15.0, help="max offset to count as 'under camera'")
    ap.add_argument("--show", action="store_true", help="show Frame and Gray windows (needs a desktop)")
    ap.add_argument("--print", action="store_true", dest="print_", help="print every reading")
    a = ap.parse_args()

    CM, dist_coef = load_calibration(a.calib)
    detector = make_detector()
    obj_pts = marker_object_points(a.marker_mm)
    cap = open_camera(a.camera, a.backend, a.width, a.height)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if a.show:                                       # two windows side by side, like the template
        cv2.namedWindow("Frame", cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow("Gray", cv2.WINDOW_AUTOSIZE)
        cv2.moveWindow("Frame", 0, 100)
        cv2.moveWindow("Gray", a.width, 100)

    log.info("Sending readings to %s:%d every %.2f s  (Ctrl+C or q to stop)", a.host, a.port, a.period)
    seq, fps, last_ids = 0, 0.0, None
    start = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                log.error("Could not read a frame; exiting")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _rejected = detector.detectMarkers(gray)

            # log only when the set of visible markers changes (as in the template)
            seen = tuple(sorted(int(i) for i in ids.flatten())) if ids is not None else ()
            if seen != last_ids:
                log.info("Visible markers: %s", seen if seen else "none")
                last_ids = seen

            poses = measure_markers(corners, ids, obj_pts, CM, dist_coef)
            mid_id, offset_mm, valid = pick_centre_marker(poses, a.axis, a.sign, a.tol_mm)

            # --- send to Simulink ---
            seq += 1
            sock.sendto(PACKET.pack(seq, mid_id, int(round(offset_mm * 10)), valid), (a.host, a.port))

            if a.print_:
                z = next((p[3] for p in poses if p[0] == mid_id), 0.0)
                print(f"seq={seq:6d} id={mid_id:3d} offset={offset_mm:7.1f} mm "
                      f"z={z:6.1f} mm valid={valid}  fps={fps:4.1f}")

            if a.show:
                if len(corners) > 0:
                    aruco.drawDetectedMarkers(frame, corners, ids)
                    for _id, _x, _y, _z, rvec, tvec in poses:
                        cv2.drawFrameAxes(frame, CM, dist_coef, rvec, tvec, a.marker_mm / 4)
                cv2.drawMarker(frame, (int(CM[0, 2]), int(CM[1, 2])), (0, 255, 0),
                               cv2.MARKER_CROSS, 30, 2)              # optical centre from calibration
                colour = (0, 255, 0) if valid else (0, 0, 255)
                cv2.putText(frame, f"id {mid_id}  {offset_mm:+.1f} mm  valid {valid}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, colour, 2)
                cv2.putText(frame, f"FPS {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imshow("Frame", frame)
                cv2.imshow("Gray", gray)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            # steady processing rate (same idea as the template)
            elapsed = time.time() - start
            if elapsed < a.period:
                time.sleep(a.period - elapsed)
            now = time.time()
            fps = 1.0 / max(now - start, 1e-6)
            start = now
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if a.show:
            cv2.destroyAllWindows()
        log.info("Camera capture stopped")


if __name__ == "__main__":
    main()