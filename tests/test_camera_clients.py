"""Pruebas sin placa: HTTP MJPEG real, ventanas simuladas y VGA/QVGA."""
import contextlib
import importlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import runpy
import sys
import threading
import unittest
from unittest.mock import patch

import cv2
import numpy as np

CLIENTS = Path(__file__).resolve().parents[1] / "Robot_OpenCV"
sys.path.insert(0, str(CLIENTS))
config = importlib.import_module("camera_config")


class CameraTests(unittest.TestCase):
    def test_urls(self):
        for value in ("192.168.43.25", "http://192.168.43.25/",
                      "http://192.168.43.25:81/stream"):
            self.assertEqual(config.stream_url(value), "http://192.168.43.25:81/stream")
        for value in ("", "https://host/", "http://user:pass@host/", "host:82",
                      "http://host/status", "host/stream?x=1"):
            with self.assertRaises(ValueError):
                config.stream_url(value)

    def test_detector_scale_and_orientation(self):
        for width, height in ((640, 480), (320, 240)):
            frame = np.full((height, width, 3), 255, np.uint8)
            frame[:, :width // 4] = 0
            resized = config.detector_frame(frame)
            self.assertEqual(resized.shape, (120, 160, 3))
            self.assertEqual(int(resized[60, 10, 0]), 0)
            self.assertEqual(int(resized[60, 150, 0]), 255)

    def test_four_clients_over_http(self):
        for width, height in ((640, 480), (320, 240)):
            frame = np.full((height, width, 3), 255, np.uint8)
            frame[:, width // 2 - 12:width // 2 + 12] = 0
            ok, encoded = cv2.imencode(".jpg", frame)
            self.assertTrue(ok)
            jpg = encoded.tobytes()
            part = (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_GET(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace;boundary=frame")
                    self.end_headers()
                    try:
                        # Varios cuadros en una respuesta, incluidos limites de lectura de 4096 bytes.
                        self.wfile.write(part * 4)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/stream"
            try:
                for name in ("camera_test.py", "deteccion_camino.py",
                             "test_fps_latency.py", "test_stream.py"):
                    with self.subTest(script=name, resolution=(width, height)):
                        shown = []
                        def show(title, image):
                            shown.append(image.shape[:2])
                        with patch.object(config, "get_stream_url", return_value=url), \
                             patch.object(cv2, "imshow", side_effect=show), \
                             patch.object(cv2, "waitKey", return_value=-1), \
                             patch.object(cv2, "destroyAllWindows"), \
                             contextlib.redirect_stdout(io.StringIO()):
                            runpy.run_path(str(CLIENTS / name), run_name="__main__")
                        if name != "test_stream.py":
                            self.assertGreaterEqual(len(shown), 4)
                        if name == "camera_test.py":
                            self.assertEqual(shown[0], (height, width))
                        if name == "test_fps_latency.py":
                            self.assertEqual(shown[0], (height, width))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
