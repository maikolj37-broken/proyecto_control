import ast
from pathlib import Path
import sys
import unittest
import contextlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import runpy
from unittest.mock import patch
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Robot_OpenCV'))
from linea_pipeline import Pipeline, Config, render
from linea_fft import anticipar


def pista(offset=0, curve=0, near_only=False):
    img = np.full((240,320,3), 240, np.uint8)
    points = []
    for y in range(240):
        x = 160 + offset + curve*((192-y)/100)**2 if y < 192 else 160+offset
        points.append((round(x), y))
    if near_only:
        points = points[150:]
    cv2.polylines(img, [np.array(points,np.int32)], False, (15,15,15), 15)
    return img


class PipelineTests(unittest.TestCase):
    def test_reused_functions_unchanged(self):
        trees = [ast.parse(p.read_text(encoding='utf-8-sig')) for p in
                 [ROOT/'Taller_Procesamiento_Imagenes/taller_opencv3.py', ROOT/'Robot_OpenCV/linea_taller.py']]
        funcs = [{n.name: ast.dump(n) for n in t.body if isinstance(n,ast.FunctionDef)} for t in trees]
        for name in ['lane','ajustar_recta','pwm']:
            self.assertEqual(funcs[0][name], funcs[1][name])

    def test_confirm_loss_and_reacquire(self):
        p = Pipeline()
        for i in range(3):
            stages, m = p.process(pista())
            self.assertEqual(m['guia_valida'], i == 2)
        self.assertLess(abs(m['error_px']), 1)
        self.assertEqual(m['direccion_visible'], 'RECTA')
        self.assertEqual(render(stages).shape, (1060,1280,3))
        for blank in [np.full((240,320,3),255,np.uint8), np.zeros((240,320,3),np.uint8)]:
            _, m = p.process(blank)
            self.assertFalse(m['guia_valida'])
            self.assertEqual(m['velocidad_relativa'], 0)
        _, m = p.process(pista())
        self.assertFalse(m['guia_valida'])

    def test_offset_and_curves(self):
        for offset in [-35,35]:
            p = Pipeline(Config(confirmar=1))
            _, m = p.process(pista(offset))
            self.assertTrue(m['guia_valida'])
            self.assertEqual(np.sign(m['giro_relativo']), np.sign(offset))
        for curve, direction in [(-35,'IZQUIERDA'),(35,'DERECHA')]:
            p = Pipeline(Config(confirmar=1))
            _, m = p.process(pista(curve=curve))
            self.assertEqual(m['direccion_visible'], direction)
            self.assertTrue(m['guia_valida'])

    def test_no_extrapolation(self):
        _, m = Pipeline(Config(confirmar=1)).process(pista(near_only=True))
        self.assertIsNotNone(m['error_px'])
        self.assertFalse(m['anticipacion_valida'])
        self.assertFalse(m['guia_valida'])
        self.assertEqual(m['velocidad_relativa'],0)

    def test_fft_suppresses_high_spatial_frequency(self):
        ys = np.arange(60,239)
        baseline = 160 + 20*np.cos((ys-60)/179*np.pi)
        noisy = baseline + 3*np.sin(2*np.pi*ys/6)
        result = anticipar([dict(y=int(y),centro_bordes_px=float(x)) for y,x in zip(ys,noisy)],240,320,5)
        self.assertIsNotNone(result)
        self.assertLess(np.sqrt(np.mean((result['suavizado']-baseline)**2)),
                        np.sqrt(np.mean((noisy-baseline)**2)))

    def test_white_and_manual(self):
        image = 255-pista()
        _, m = Pipeline(Config(linea='blanca', modo='manual', umbral=100, confirmar=1)).process(image)
        self.assertTrue(m['guia_valida'])

    def test_config_rejects_invalid(self):
        for cfg in [Config(gamma=0),Config(gamma=float('nan')),Config(armonicos=0),Config(rmse_max=-1)]:
            with self.assertRaises(ValueError):
                Pipeline(cfg)

    def test_live_runner_with_http_mjpeg(self):
        ok, jpg = cv2.imencode('.jpg', pista(curve=25))
        self.assertTrue(ok)
        data = jpg.tobytes()
        part = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(data)).encode() + b'\r\n\r\n' + data + b'\r\n'
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type','multipart/x-mixed-replace;boundary=frame')
                self.end_headers()
                try:
                    for _ in range(40):
                        self.wfile.write(part)
                        self.wfile.flush()
                        time.sleep(.04)
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        output = io.StringIO()
        try:
            with patch('camera_config.stream_url',return_value=f'http://127.0.0.1:{server.server_port}/stream'), \
                 patch.object(sys,'argv',['seguimiento_linea.py','--ip','prueba','--sin-ventana','--max-cuadros','8']), \
                 contextlib.redirect_stdout(output):
                runpy.run_path(str(ROOT/'Robot_OpenCV/seguimiento_linea.py'),run_name='__main__')
            self.assertIn('8 cuadros procesados',output.getvalue())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
