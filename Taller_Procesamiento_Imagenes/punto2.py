"""
CONTROL 2 - Taller de clase
Punto 2: Aplicar la operación gama (ver tutorial de OpenCV sobre
transformaciones lineales básicas) sobre:
  a) el canal V (Value) de la imagen HSV
  b) la imagen en escala de grises
para varios valores de gama, y así poder responder cuál gama mejora la imagen.

Formula de la transformación gama:
    O = 255 * (I / 255) ** gama
  - gama < 1  -> aclara la imagen (realza detalles en zonas oscuras)
  - gama > 1  -> oscurece la imagen (realza detalles en zonas claras)
  - gama = 1  -> no cambia nada

Salidas en la carpeta de resultados (resultados/):
  - clip_V_gama_<g>.mp4     -> canal V corregido, para cada gama
  - clip_gris_gama_<g>.mp4  -> gris corregido, para cada gama
  - frames_punto2/          -> cuadros de muestra por segundo, en los 2 formatos, para cada gama
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN (EDITA ESTO) ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
VIDEO_ENTRADA = os.path.join(CARPETA_TALLER, "ideal.mp4")
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")

DURACION_CLIP_SEG = 15
SEGUNDO_INICIO = 0

# Valores de gama que se van a comparar (agrega o quita los que quieras probar)
VALORES_GAMA = [0.4, 0.7, 1.0, 1.5, 2.2]
# ======================================================================

CARPETA_FRAMES = os.path.join(CARPETA_RESULTADOS, "frames_punto2")

os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)


def correccion_gama(canal, gama):
    """Aplica la transformación gama a una imagen de 1 canal (8 bits) usando una LUT."""
    tabla = np.array([((i / 255.0) ** gama) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(canal, tabla)


cap = cv2.VideoCapture(VIDEO_ENTRADA)
if not cap.isOpened():
    raise IOError(f"No se pudo abrir el video: {VIDEO_ENTRADA}")

fps = cap.get(cv2.CAP_PROP_FPS)
ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

frame_inicio = int(SEGUNDO_INICIO * fps)
num_frames_clip = int(DURACION_CLIP_SEG * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_inicio)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writers_v = {}
writers_gray = {}
for g in VALORES_GAMA:
    tag = str(g).replace(".", "_")
    writers_v[g] = cv2.VideoWriter(
        os.path.join(CARPETA_RESULTADOS, f"clip_V_gama_{tag}.mp4"), fourcc, fps, (ancho, alto), isColor=False
    )
    writers_gray[g] = cv2.VideoWriter(
        os.path.join(CARPETA_RESULTADOS, f"clip_gris_gama_{tag}.mp4"), fourcc, fps, (ancho, alto), isColor=False
    )

contador = 0
while contador < num_frames_clip:
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    _, _, v = cv2.split(hsv)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for g in VALORES_GAMA:
        v_corregido = correccion_gama(v, g)
        gray_corregido = correccion_gama(gray, g)

        writers_v[g].write(v_corregido)
        writers_gray[g].write(gray_corregido)

        if contador % int(round(fps)) == 0:
            tag = str(g).replace(".", "_")
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_V_gama_{tag}.png"), v_corregido)
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_gris_gama_{tag}.png"), gray_corregido)

    contador += 1

cap.release()
for g in VALORES_GAMA:
    writers_v[g].release()
    writers_gray[g].release()

print(f"Listo. Se procesaron {contador} cuadros con {len(VALORES_GAMA)} valores de gama: {VALORES_GAMA}")
print(f"Resultados guardados en: {CARPETA_RESULTADOS}")
print("Revisa las imágenes/videos y compara cuál gama mejora más la visibilidad de la línea.")