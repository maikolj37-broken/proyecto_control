"""Taller en vivo: identificación de línea, FFT espacial y referencias de guía."""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import threading
import time

import cv2
from camera_config import stream_url, open_capture
from linea_pipeline import Config, Pipeline, TITLES, render


class LatestStream:
    """Drena el stream continuamente y conserva solo el último cuadro recibido."""
    def __init__(self, cap):
        self.cap = cap
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.latest = None
        self.ended = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        seq = 0
        try:
            while not self.stop.is_set():
                ok, frame = self.cap.read()
                if not ok:
                    break
                seq += 1
                with self.lock:
                    self.latest = (seq, time.monotonic(), frame)
        finally:
            self.cap.release()
            self.ended = True

    def read(self):
        with self.lock:
            return self.latest

    def close(self):
        self.stop.set()
        self.thread.join(timeout=11)


class Recorder:
    def __init__(self, config, enabled=False):
        self.config, self.enabled = config, enabled
        self.folder = None
        self.file = None
        self.writer = None

    def prepare(self):
        if self.folder is None:
            self.folder = Path(__file__).resolve().parent / 'resultados_seguimiento' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            self.folder.mkdir(parents=True)
            (self.folder/'config.json').write_text(json.dumps(asdict(self.config), indent=2), encoding='utf-8')
            print('Resultados:', self.folder)

    def log(self, record):
        if not self.enabled:
            return
        self.prepare()
        if self.file is None:
            self.file = (self.folder/'mediciones.csv').open('w', newline='', encoding='utf-8')
            self.writer = csv.DictWriter(self.file, fieldnames=list(record))
            self.writer.writeheader()
        self.writer.writerow(record)
        self.file.flush()

    def snapshot(self, seq, stages):
        self.prepare()
        target = self.folder/f'cuadro_{seq:06d}'
        target.mkdir(exist_ok=True)
        for i, frame in enumerate(stages):
            if not cv2.imwrite(str(target/f'etapa_{i+1:02d}.png'), frame):
                raise OSError('No se pudo guardar la etapa')
        cv2.imwrite(str(target/'panel.png'), render(stages))
        (target/'etapas.json').write_text(json.dumps(TITLES, indent=2), encoding='utf-8')

    def close(self):
        if self.file:
            self.file.close()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group()
    source.add_argument('--ip', '--url', dest='ip', default=os.getenv('ROBOT_CAMERA_IP', ''))
    source.add_argument('--video', type=Path, help='Video local para repetir una prueba, sin cámara')
    p.add_argument('--gamma', type=float, default=1.)
    p.add_argument('--modo', choices=['otsu','manual'], default='otsu')
    p.add_argument('--umbral', type=int, default=80)
    p.add_argument('--linea', choices=['negra','blanca'], default='negra')
    p.add_argument('--rmse-max', type=float, default=3.)
    p.add_argument('--confirmar', type=int, default=3)
    p.add_argument('--armonicos', type=int, default=5)
    p.add_argument('--edad-max', type=float, default=.5, help='Máximo tiempo sin un nuevo cuadro recibido (s)')
    p.add_argument('--guardar', action='store_true', help='Registrar CSV y configuración por sesión')
    p.add_argument('--sin-ventana', action='store_true')
    p.add_argument('--max-cuadros', type=int, default=0, help='0 = sin límite')
    return p


def main():
    p = parser()
    args = p.parse_args()
    cfg = Config(gamma=args.gamma, modo=args.modo, umbral=args.umbral, linea=args.linea,
                 rmse_max=args.rmse_max, confirmar=args.confirmar, armonicos=args.armonicos)
    try:
        cfg.validate()
        if not 0 < args.edad_max <= 10 or args.max_cuadros < 0:
            raise ValueError('Edad máxima: (0, 10] segundos; max-cuadros >= 0.')
    except ValueError as exc:
        p.error(str(exc))
    if args.video:
        cap = cv2.VideoCapture(str(args.video))
        if not cap.isOpened():
            p.error(f'No se pudo abrir {args.video}')
        live = None
    else:
        try:
            ip = args.ip or input('IP de la cámara (monitor serie): ')
            url = stream_url(ip)
        except (ValueError, EOFError, KeyboardInterrupt) as exc:
            p.error(str(exc))
        print('Stream:', url, '| Cierra otros clientes de video.')
        cap = open_capture(url)
        live = LatestStream(cap)
    pipeline, recorder = Pipeline(cfg), Recorder(cfg, args.guardar)
    title = 'Taller en vivo - guia visual (sin motores)'
    if not args.sin_ventana:
        cv2.namedWindow(title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(title, 1200, 900)
    print('M: mosaico | N/P: etapa siguiente/anterior | Espacio: pausa | S: guardar etapas | Q: salir')
    print('FFT espacial: anticipa solo la pista visible; no estima velocidad física ni curvas ocultas.')
    selected, paused, last_seq, count = None, False, 0, 0
    last_report, started, last_received = 0., time.monotonic(), time.monotonic()
    stages = record = None
    try:
        while True:
            key = -1 if args.sin_ventana else cv2.waitKey(1) & 255
            if key == ord('q'):
                break
            if key == ord('m'):
                selected = None
            elif key in (ord('n'), ord('p')):
                selected = (0 if selected is None else (selected + (1 if key == ord('n') else -1)) % len(TITLES))
            elif key == ord(' '):
                paused = not paused
                pipeline.reset()
            elif key == ord('s') and stages is not None:
                recorder.snapshot(last_seq, stages)

            sample = None
            if live:
                newest = live.read()
                if newest is not None and newest[0] != last_seq:
                    sample = newest
                if live.ended and sample is None:
                    print('STREAM TERMINADO: referencia de velocidad cero.')
                    break
            elif not paused:
                ok, frame = cap.read()
                if not ok:
                    break
                sample = (last_seq+1, time.monotonic(), frame)

            if sample:
                last_seq, received, frame = sample
                last_received = received
                if not paused and time.monotonic()-received <= args.edad_max:
                    t0 = time.monotonic()
                    stages, metric = pipeline.process(frame)
                    count += 1
                    record = dict(cuadro=last_seq, tiempo_s=time.monotonic()-started,
                                  procesamiento_ms=1000*(time.monotonic()-t0), **metric)
                    recorder.log(record)
                    if time.monotonic()-last_report >= 1:
                        print(f"{metric['estado']} | e={metric['error_px']} px | "
                              f"adelante={metric['direccion_visible']} | giro={metric['giro_relativo']:+.3f} | "
                              f"vel.rel={metric['velocidad_relativa']:.3f}")
                        last_report = time.monotonic()
            stale = live is not None and time.monotonic()-last_received > args.edad_max
            if paused or stale:
                pipeline.reset()
                if record is not None:
                    record = dict(record, tiempo_s=time.monotonic()-started,
                                  estado='PAUSA' if paused else 'SIN_CUADRO_NUEVO',
                                  guia_valida=False, giro_relativo=0., velocidad_relativa=0.,
                                  pwm_taller_izquierdo=0., pwm_taller_derecho=0.)
                if time.monotonic()-last_report >= 1:
                    print('PAUSA' if paused else 'SIN CUADRO NUEVO', '| guía inválida, velocidad=0')
                    if record:
                        recorder.log(record)
                    last_report = time.monotonic()
            if stages is not None and not args.sin_ventana:
                if paused or stale:
                    frozen = [frame.copy() for frame in stages]
                    frozen[-1][:] = 0
                    cv2.putText(frozen[-1], 'GUIA INVALIDA / VELOCIDAD=0', (5,100),
                                cv2.FONT_HERSHEY_SIMPLEX, .45, (0,180,255), 1)
                    view = render(frozen, selected)
                    cv2.rectangle(view, (0,0), (view.shape[1],35), (0,0,0), -1)
                    cv2.putText(view, 'CUADRO CONGELADO - SIN GUIA ACTUAL',
                                (8,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,180,255), 2)
                else:
                    view = render(stages, selected)
                cv2.imshow(title, view)
            if args.max_cuadros and count >= args.max_cuadros:
                break
            if sample is None or paused:
                time.sleep(.01)
    except KeyboardInterrupt:
        pass
    finally:
        if record:
            recorder.log(dict(record, tiempo_s=time.monotonic()-started, estado='FINALIZADO',
                              guia_valida=False, velocidad_relativa=0., giro_relativo=0.,
                              pwm_taller_izquierdo=0., pwm_taller_derecho=0.))
        if live:
            live.close()
        else:
            cap.release()
        recorder.close()
        cv2.destroyAllWindows()
    print(f'Fin: {count} cuadros procesados. No se enviaron órdenes a motores.')


if __name__ == '__main__':
    main()
