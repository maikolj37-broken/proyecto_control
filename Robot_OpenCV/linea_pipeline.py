"""Etapas de visión y seguimiento visual basadas en los talleres existentes."""
from dataclasses import dataclass
import math
import cv2
import numpy as np
from linea_taller import lane, ajustar_recta, pwm
from linea_fft import anticipar, panels


@dataclass
class Config:
    gamma: float = 1.0
    modo: str = "otsu"
    umbral: int = 80
    linea: str = "negra"
    base: float = 110.0
    kp: float = 70.0
    rmse_max: float = 3.0
    confirmar: int = 3
    armonicos: int = 5

    def validate(self):
        for value in (self.gamma, self.base, self.kp, self.rmse_max):
            if not math.isfinite(value):
                raise ValueError("Los parámetros deben ser finitos.")
        if not .1 <= self.gamma <= 5 or not 0 <= self.umbral <= 255:
            raise ValueError("Gamma: 0.1 a 5; umbral: 0 a 255.")
        if self.modo not in ("otsu", "manual") or self.linea not in ("negra", "blanca"):
            raise ValueError("Modo o color de línea inválido.")
        if not 0 <= self.base <= 255 or not 0 <= self.kp <= 255:
            raise ValueError("Base y Kp deben estar entre 0 y 255.")
        if self.rmse_max <= 0 or self.confirmar < 1:
            raise ValueError("RMSE y número de confirmaciones deben ser positivos.")
        if not 1 <= self.armonicos <= 30:
            raise ValueError("Armonicos FFT: entre 1 y 30.")


class Pipeline:
    def __init__(self, config=None):
        self.config = config or Config()
        self.config.validate()
        self.validos = 0
        self.lut = np.array([255 * (i / 255.) ** self.config.gamma
                             for i in range(256)], dtype=np.uint8)

    def reset(self):
        self.validos = 0

    def process(self, frame):
        cfg = self.config
        image = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gamma = cv2.LUT(gray, self.lut)
        filtered = cv2.medianBlur(gamma, 3)
        polarity = cv2.THRESH_BINARY_INV if cfg.linea == "negra" else cv2.THRESH_BINARY
        threshold, binary = cv2.threshold(filtered, 0 if cfg.modo == "otsu" else cfg.umbral,
                                          255, polarity | (cv2.THRESH_OTSU if cfg.modo == "otsu" else 0))
        _, raw_binary = cv2.threshold(gray, 0, 255, polarity | cv2.THRESH_OTSU)
        difference = cv2.absdiff(binary, raw_binary)
        kernel = np.ones((3, 3), np.uint8)
        clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, borderType=cv2.BORDER_REPLICATE)
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, borderType=cv2.BORDER_REPLICATE)
        clean[:int(.25*h)] = 0
        mask, border, gx, rows = lane(binary)
        fit = ajustar_recta(rows, h, w)
        fft = anticipar(rows, h, w, cfg.armonicos)
        reason = "SIN_LINEA" if not rows else "SIN_AJUSTE"
        if fit is not None:
            reason = "AJUSTE_RUIDOSO" if fit['rmse_ortogonal_px'] > cfg.rmse_max else "VALIDA"
        self.validos = self.validos + 1 if reason == "VALIDA" else 0
        tracking = self.validos >= cfg.confirmar
        state = "SEGUIMIENTO_VISUAL" if tracking else ("CONFIRMANDO" if reason == "VALIDA" else reason)
        error = fit['error_recta_px'] if fit is not None else None
        left, right = pwm(error or 0, tracking, w, cfg.base, cfg.kp)
        centers = image.copy()
        cv2.line(centers, ((w-1)//2, 0), ((w-1)//2, h-1), (255, 150, 0), 1)
        for r in rows:
            y = r['y']
            cv2.circle(centers, (round(r['centro_bordes_px']), y), 1, (0, 145, 255), -1)
            centers[y, r['izquierda_px']] = (255, 255, 0)
            centers[y, r['derecha_px']] = (255, 255, 0)
        result = centers.copy()
        if fit:
            pts = [(round(fit['x0']+(y-fit['y0'])*fit['vx']/fit['vy']), round(y))
                   for y in (fit['y_min'], fit['y_max'])]
            visible, p1, p2 = cv2.clipLine((0, 0, w, h), *pts)
            if visible:
                cv2.line(result, p1, p2, (0, 220, 0), 2)
            cv2.circle(result, (round(fit['centro_recta_px']), round(fit['fila_referencia_px'])),
                       4, (255, 0, 255), -1)
        cv2.rectangle(result, (0, 0), (w, 53), (0, 0, 0), -1)
        for i, text in enumerate((state, f"e={error:.1f}px" if error is not None else "e=sin datos",
                                  'Ajuste local entre 65% y 90% H')):
            cv2.putText(result, text, (5, 14 + i*17), cv2.FONT_HERSHEY_SIMPLEX, .42,
                        (0, 220, 0) if tracking else (0, 180, 255), 1)
        masked = cv2.bitwise_and(gamma, gamma, mask=mask)
        stages = [image, gray, gamma, filtered, binary, difference, clean, mask,
                  masked, border, centers, result]
        metric = dict(estado=state, filas=len(rows), umbral=threshold,
                      error_px=error, error_normalizado=error/((w-1)/2) if error is not None else None,
                      rmse_px=fit['rmse_ortogonal_px'] if fit else None,
                      pwm_taller_izquierdo=left, pwm_taller_derecho=right,
                      distancia_cm="SIN_CALIBRACION", motores="NO_CONECTADOS")
        # Referencia exploratoria adimensional; no sustituye al controlador de motores.
        guidance_valid = tracking and fft is not None
        angle = fft['angulo_deg'] if fft else None
        turn = float(np.clip(.6*(error/((w-1)/2)) + .4*np.sin(np.radians(angle)), -1, 1)) if guidance_valid else 0.
        speed = float(np.clip(1-.7*abs(turn)-.4*abs(angle)/90, .2, 1)) if guidance_valid else 0.
        metric.update(guia_valida=guidance_valid, anticipacion_valida=fft is not None,
                      angulo_imagen_deg=angle, direccion_visible=fft['direccion'] if fft else 'DESCONOCIDA',
                      desplazamiento_visible_px=fft['desplazamiento_px'] if fft else None,
                      residuo_fft_px=fft['residuo_fft_px'] if fft else None,
                      giro_relativo=turn, velocidad_relativa=speed)
        profile, spectrum, preview = panels(fft, image)
        guide = np.zeros_like(image)
        lines = ['GUIA AL CONTROLADOR (sin envio)',
                 'VALIDA' if guidance_valid else 'PARAR / GUIA NO VALIDA',
                 f'Giro relativo: {turn:+.3f}', f'Velocidad relativa: {speed:.3f}',
                 'Positivo = derecha en imagen', 'No son rad/s ni m/s',
                 'FFT: anticipacion SOLO visible']
        for i, text in enumerate(lines):
            cv2.putText(guide, text, (5,25+i*27), cv2.FONT_HERSHEY_SIMPLEX, .43,
                        (0,230,0) if guidance_valid else (0,180,255), 1)
        stages.extend([profile, spectrum, preview, guide])
        return stages, metric


TITLES = ("01 Original 320x240", "02 Escala de grises", "03 Correccion gamma",
          "04 Filtro mediana 3x3", "05 Segmentacion", "06 Diferencia vs Otsu gris",
          "07 Apertura/cierre + ROI", "08 Componente de linea", "09 Mascara aplicada",
          "10 Bordes morfologicos", "11 Centros por fila", "12 Ajuste L2 y seguimiento",
          "13 Perfil x(y) filtrado FFT", "14 Espectro espacial FFT",
          "15 Anticipacion visible", "16 Referencias de guia")


def render(stages, selected=None):
    tiles = []
    indices = range(len(stages)) if selected is None else [selected]
    for i in indices:
        frame = stages[i]
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        tile = cv2.copyMakeBorder(frame, 25, 0, 0, 0, cv2.BORDER_CONSTANT)
        cv2.putText(tile, TITLES[i], (5, 17), cv2.FONT_HERSHEY_SIMPLEX, .43, (255,255,255), 1)
        tiles.append(tile)
    if selected is not None:
        return cv2.resize(tiles[0], (640, 530), interpolation=cv2.INTER_NEAREST)
    return np.vstack([np.hstack(tiles[i:i+4]) for i in range(0, len(tiles), 4)])
