"""
CONTROL 2 - Taller de clase
Punto 1: Extraer un clip de 15 segundos de "ideal.mp4", convertir cada
cuadro de RGB (BGR en OpenCV) a HSV, y convertir también a escala de grises.

Salidas en la carpeta de resultados (resultados/):
  - clip_rgb.mp4   -> el clip original recortado
  - clip_hsv.mp4   -> el clip en HSV, reconvertido a BGR solo para poder visualizarlo
  - clip_gris.mp4  -> el clip en escala de grises
  - frames_punto1/ -> un cuadro representativo por segundo, en los 3 formatos
"""

import cv2
import os

# ==================== CONFIGURACIÓN (EDITA ESTO) ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
VIDEO_ENTRADA = os.path.join(CARPETA_TALLER, "ideal.mp4")
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")

DURACION_CLIP_SEG = 15     # duración del clip a extraer
SEGUNDO_INICIO = 0         # segundo del video original donde empieza el clip
# ======================================================================

CARPETA_FRAMES = os.path.join(CARPETA_RESULTADOS, "frames_punto1")

os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)

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
writer_rgb = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_rgb.mp4"), fourcc, fps, (ancho, alto))
writer_hsv = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_hsv.mp4"), fourcc, fps, (ancho, alto))
writer_gray = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_gris.mp4"), fourcc, fps, (ancho, alto), isColor=False)

contador = 0
while contador < num_frames_clip:
    ret, frame = cap.read()
    if not ret:
        break

    # Paso clave 1: BGR -> HSV
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Paso clave 2: BGR -> escala de grises
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    writer_rgb.write(frame)
    # Para poder VER el HSV como video normal hay que reconvertirlo a BGR al guardarlo
    writer_hsv.write(cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR))
    writer_gray.write(frame_gray)

    # Un cuadro de muestra por segundo, útil para pegar en el informe
    if contador % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_rgb.png"), frame)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_hsv.png"),
                    cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR))
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_gris.png"), frame_gray)

    contador += 1

cap.release()
writer_rgb.release()
writer_hsv.release()
writer_gray.release()

print(f"Listo. Se procesaron {contador} cuadros ({contador / fps:.2f} s).")
print(f"Resultados guardados en: {CARPETA_RESULTADOS}")