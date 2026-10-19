"""
CONTROL 2 - Taller de clase
Punto 3: Aplicar una transformación de perspectiva a cada cuadro del clip
para que la línea tenga el mismo ancho en todos los cuadros.

Modo de uso:
  1. Corre el script. Se abre una ventana con el primer cuadro del clip.
  2. Haz clic, EN ESTE ORDEN, en las 4 esquinas de la región que quieres
     "enderezar" (por ejemplo, las 2 esquinas donde la línea se ve más
     ancha -cerca de la cámara- y las 2 esquinas donde se ve más angosta
     -más lejos-):
        1) superior-izquierda   2) superior-derecha
        3) inferior-derecha     4) inferior-izquierda
  3. Presiona cualquier tecla (o espera a completar los 4 clics) para
     continuar. El script calcula la homografía y la aplica a TODOS los
     cuadros del clip, asumiendo que la cámara no se mueve durante el clip.

Salidas:
  - clip_perspectiva.mp4  -> clip corregido, en resultados/
  - frames_punto3/        -> cuadros de muestra (original vs corregido)
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
VIDEO_ENTRADA = os.path.join(CARPETA_TALLER, "ideal.mp4")
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_FRAMES = os.path.join(CARPETA_RESULTADOS, "frames_punto3")

DURACION_CLIP_SEG = 15
SEGUNDO_INICIO = 0
# ==========================================================

os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)

puntos_src = []


def click_evento(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(puntos_src) < 4:
        puntos_src.append((x, y))
        print(f"Punto {len(puntos_src)}: ({x}, {y})")


cap = cv2.VideoCapture(VIDEO_ENTRADA)
if not cap.isOpened():
    raise IOError(f"No se pudo abrir el video: {VIDEO_ENTRADA}")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_inicio = int(SEGUNDO_INICIO * fps)
num_frames_clip = int(DURACION_CLIP_SEG * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_inicio)

ret, primer_cuadro = cap.read()
if not ret:
    raise IOError("No se pudo leer el primer cuadro del clip.")

# --------- Selección manual de las 4 esquinas ---------
ventana = "Selecciona 4 puntos: sup-izq, sup-der, inf-der, inf-izq (ESC cancela)"
clon = primer_cuadro.copy()
cv2.namedWindow(ventana)
cv2.setMouseCallback(ventana, click_evento)

while True:
    vista = clon.copy()
    for i, p in enumerate(puntos_src):
        cv2.circle(vista, p, 5, (0, 0, 255), -1)
        cv2.putText(vista, str(i + 1), p, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.imshow(ventana, vista)
    tecla = cv2.waitKey(20) & 0xFF
    if len(puntos_src) == 4 or tecla == 27:
        break

cv2.destroyAllWindows()

if len(puntos_src) != 4:
    raise ValueError("Debes seleccionar exactamente 4 puntos para continuar.")

src = np.float32(puntos_src)

# --------- Rectángulo destino con el MISMO ancho arriba y abajo ---------
ancho_destino = int(max(
    np.linalg.norm(src[0] - src[1]),
    np.linalg.norm(src[3] - src[2])
))
alto_destino = int(max(
    np.linalg.norm(src[0] - src[3]),
    np.linalg.norm(src[1] - src[2])
))

dst = np.float32([
    [0, 0],
    [ancho_destino - 1, 0],
    [ancho_destino - 1, alto_destino - 1],
    [0, alto_destino - 1]
])

M = cv2.getPerspectiveTransform(src, dst)

# --------- Aplicar la misma transformación a todo el clip ---------
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_inicio)  # reiniciar al inicio del clip

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_perspectiva.mp4"),
                          fourcc, fps, (ancho_destino, alto_destino))

contador = 0
while contador < num_frames_clip:
    ret, frame = cap.read()
    if not ret:
        break

    frame_corregido = cv2.warpPerspective(frame, M, (ancho_destino, alto_destino))
    writer.write(frame_corregido)

    if contador % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_original.png"), frame)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_corregido.png"), frame_corregido)

    contador += 1

cap.release()
writer.release()

print(f"Listo. Homografía aplicada a {contador} cuadros.")
print(f"Resultados guardados en: {CARPETA_RESULTADOS}")