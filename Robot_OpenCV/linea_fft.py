"""Filtrado espacial de x(y); anticipación sobre pista visible, sin extrapolar."""
import cv2
import numpy as np


def anticipar(rows, h, w, harmonics=5):
    points = sorted((r['y'], r['centro_bordes_px']) for r in rows)
    if len(points) < .35*h:
        return None
    ys, xs = np.array(points, dtype=float).T
    far, near = round(.45*h), round(.8*h)
    if ys.min() > far or ys.max() < near or np.max(np.diff(ys)) > .05*h:
        return None
    grid = np.arange(int(ys.min()), int(ys.max())+1)
    raw = np.interp(grid, ys, xs)
    # Retirar tendencia evita que el filtrado cambie la pendiente de una recta.
    trend = np.linspace(raw[0], raw[-1], len(raw))
    residual = raw - trend
    # Extensión reflejada evita unir bruscamente el inicio con el final.
    extended = np.r_[residual, residual[-2:0:-1]]
    spectrum = np.fft.rfft(extended)
    filtered = spectrum.copy()
    filtered[harmonics+1:] = 0
    smooth = np.fft.irfft(filtered, n=len(extended))[:len(raw)] + trend
    if np.any(smooth < 0) or np.any(smooth >= w):
        return None
    xfar, xnear = np.interp([far, near], grid, smooth)
    delta = float(xfar-xnear)
    angle = float(np.degrees(np.arctan2(delta, near-far)))
    direction = 'DERECHA' if delta > .03*w else 'IZQUIERDA' if delta < -.03*w else 'RECTA'
    return dict(y=grid, original=raw, suavizado=smooth, espectro=np.abs(spectrum),
                filtrado=np.abs(filtered), x_lejano=float(xfar), x_cercano=float(xnear),
                y_lejano=far, y_cercano=near, angulo_deg=angle,
                desplazamiento_px=delta, direccion=direction,
                residuo_fft_px=float(np.sqrt(np.mean((raw-smooth)**2))))


def panels(fft, image):
    h, w = image.shape[:2]
    profile = np.zeros_like(image)
    spectrum = np.zeros_like(image)
    preview = image.copy()
    if fft is None:
        for panel in (profile, spectrum, preview):
            cv2.putText(panel, 'SIN COBERTURA PARA FFT', (8, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, .48, (0,180,255), 1)
        return profile, spectrum, preview
    for key, color in [('original', (0,145,255)), ('suavizado', (0,255,0))]:
        pts = np.c_[fft[key], fft['y']].round().astype(np.int32)
        cv2.polylines(profile, [pts], False, color, 1)
    cv2.putText(profile, 'Naranja: centros / verde: FFT', (4,16),
                cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
    maxval = max(float(np.log1p(fft['espectro']).max()), 1.)
    for key, color in [('espectro', (0,145,255)), ('filtrado', (0,255,0))]:
        values = np.log1p(fft[key])
        pts = np.c_[np.linspace(5,w-5,len(values)), h-20-values/maxval*(h-50)].astype(np.int32)
        cv2.polylines(spectrum, [pts], False, color, 1)
    cv2.putText(spectrum, 'log(1+|F|) vs indice espacial', (4,16),
                cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
    near = (round(fft['x_cercano']), fft['y_cercano'])
    far = (round(fft['x_lejano']), fft['y_lejano'])
    cv2.arrowedLine(preview, near, far, (255,0,255), 2)
    cv2.putText(preview, f"{fft['direccion']} {fft['angulo_deg']:+.1f} deg imagen", (4,16),
                cv2.FONT_HERSHEY_SIMPLEX, .44, (0,180,255), 1)
    return profile, spectrum, preview
