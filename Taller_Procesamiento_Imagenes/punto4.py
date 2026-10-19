"""
CONTROL 2 - Taller de clase
Punto 4: Extraer un clip de 15s de "oscuro.mp4" y filtrarlo con 3
algoritmos distintos para reducir ruido:
  a) mascara-promedio (filtro de media)
  b) el mejor vecino  (reemplaza cada pixel por el valor del vecino
     más parecido a él, en vez de promediar)
  c) filtro mediana

Salidas:
  - clip_promedio.mp4, clip_mejor_vecino.mp4, clip_mediana.mp4 -> en resultados/
  - frames_punto4/ -> cuadros de muestra: original + los 3 filtros
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
VIDEO_ENTRADA = os.path.join(CARPETA_TALLER, "oscuro.mp4")
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_FRAMES = os.path.join(CARPETA_RESULTADOS, "frames_punto4")

DURACION_CLIP_SEG = 15
SEGUNDO_INICIO = 0
TAMANO_VENTANA = 3   # ventana kxk para los 3 filtros (debe ser impar)
# ==========================================================

os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)


def filtro_mejor_vecino(imagen, k=3):
    """
    Para cada pixel, busca -entre sus vecinos en una ventana kxk (sin
    contar el centro)- el valor MAS PARECIDO al del propio pixel, y lo
    reemplaza por ese valor. Ayuda a suavizar ruido sin perder tanto
    detalle/contraste como un promedio simple. Se aplica canal por canal.
    """
    pad = k // 2
    canales = cv2.split(imagen)
    salida_canales = []

    for canal in canales:
        canal_pad = cv2.copyMakeBorder(canal, pad, pad, pad, pad, cv2.BORDER_REFLECT)
        alto, ancho = canal.shape

        vecinos = []
        for dy in range(k):
            for dx in range(k):
                if dy == pad and dx == pad:
                    continue  # se excluye el centro
                vecinos.append(canal_pad[dy:dy + alto, dx:dx + ancho])
        vecinos = np.stack(vecinos, axis=-1).astype(np.int16)

        centro = canal.astype(np.int16)[:, :, None]
        diferencias = np.abs(vecinos - centro)
        indice_mejor = np.argmin(diferencias, axis=-1)

        resultado = np.take_along_axis(vecinos, indice_mejor[:, :, None], axis=-1)[:, :, 0]
        salida_canales.append(resultado.astype(np.uint8))

    return cv2.merge(salida_canales)


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
writer_promedio = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_promedio.mp4"), fourcc, fps, (ancho, alto))
writer_vecino = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_mejor_vecino.mp4"), fourcc, fps, (ancho, alto))
writer_mediana = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_mediana.mp4"), fourcc, fps, (ancho, alto))

contador = 0
while contador < num_frames_clip:
    ret, frame = cap.read()
    if not ret:
        break

    # a) máscara-promedio: cada pixel se reemplaza por el promedio de su ventana
    frame_promedio = cv2.blur(frame, (TAMANO_VENTANA, TAMANO_VENTANA))

    # b) el mejor vecino
    frame_vecino = filtro_mejor_vecino(frame, TAMANO_VENTANA)

    # c) filtro mediana
    frame_mediana = cv2.medianBlur(frame, TAMANO_VENTANA)

    writer_promedio.write(frame_promedio)
    writer_vecino.write(frame_vecino)
    writer_mediana.write(frame_mediana)

    if contador % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_original.png"), frame)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_promedio.png"), frame_promedio)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_mejor_vecino.png"), frame_vecino)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{contador:04d}_mediana.png"), frame_mediana)

    contador += 1

cap.release()
writer_promedio.release()
writer_vecino.release()
writer_mediana.release()

print(f"Listo. Se filtraron {contador} cuadros con los 3 algoritmos.")
print(f"Resultados guardados en: {CARPETA_RESULTADOS}")