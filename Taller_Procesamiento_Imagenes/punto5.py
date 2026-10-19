"""
CONTROL 2 - Taller de clase
Punto 5: Trabajo con histogramas sobre "ideal.mp4".
  a) Histograma del cuadro 10 del clip -> se elige un valor de umbral y
     se umbralizan TODOS los cuadros con ese mismo valor.
  b) Se busca el cuadro con MENOS línea negra (mínima cantidad de
     píxeles oscuros) y se calcula su histograma -> ese es el histograma
     de "referencia".
  c) Los demás cuadros se modifican por "especificación de histograma"
     (histogram matching) usando el histograma de b) como referencia.

Salidas:
  - clip_umbralizado.mp4          -> resultado de la parte a), en resultados/
  - clip_histograma_igualado.mp4  -> resultado de la parte c), en resultados/
  - frames_punto5/                -> histogramas (.png) + cuadros de muestra
                                       de cada parte
"""

import cv2
import numpy as np
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
VIDEO_ENTRADA = os.path.join(CARPETA_TALLER, "ideal.mp4")
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_FRAMES = os.path.join(CARPETA_RESULTADOS, "frames_punto5")

DURACION_CLIP_SEG = 15
SEGUNDO_INICIO = 0

# Umbral para la parte a). Revisa primero "histograma_cuadro10.png" y
# ajusta este valor según dónde veas el valle entre el fondo y la línea.
VALOR_UMBRAL = 80

# Un pixel se considera parte de la "línea" (negro) si es menor a esto,
# usado en la parte b) para encontrar el cuadro con menos línea.
UMBRAL_NEGRO = 50
# ==========================================================

os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)


def guardar_histograma(imagen_gris, ruta, titulo):
    hist = cv2.calcHist([imagen_gris], [0], None, [256], [0, 256])
    plt.figure()
    plt.title(titulo)
    plt.xlabel("Intensidad")
    plt.ylabel("Cantidad de píxeles")
    plt.plot(hist)
    plt.xlim([0, 256])
    plt.savefig(ruta)
    plt.close()
    return hist


def igualar_por_histograma_referencia(imagen_gris, hist_referencia):
    """
    Especificación de histograma (histogram matching): transforma
    imagen_gris para que su histograma se parezca al histograma de
    referencia, emparejando las funciones de distribución acumulada (CDF).
    """
    hist_img = cv2.calcHist([imagen_gris], [0], None, [256], [0, 256]).flatten()
    cdf_img = np.cumsum(hist_img) / np.sum(hist_img)

    hist_ref = hist_referencia.flatten()
    cdf_ref = np.cumsum(hist_ref) / np.sum(hist_ref)

    tabla_mapeo = np.zeros(256, dtype=np.uint8)
    for nivel in range(256):
        diferencias = np.abs(cdf_img[nivel] - cdf_ref)
        tabla_mapeo[nivel] = np.argmin(diferencias)

    return cv2.LUT(imagen_gris, tabla_mapeo)


# ==================== Leer todos los cuadros del clip en gris ====================
cap = cv2.VideoCapture(VIDEO_ENTRADA)
if not cap.isOpened():
    raise IOError(f"No se pudo abrir el video: {VIDEO_ENTRADA}")

fps = cap.get(cv2.CAP_PROP_FPS)
ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

frame_inicio = int(SEGUNDO_INICIO * fps)
num_frames_clip = int(DURACION_CLIP_SEG * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_inicio)

cuadros_gris = []
while len(cuadros_gris) < num_frames_clip:
    ret, frame = cap.read()
    if not ret:
        break
    cuadros_gris.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
cap.release()

print(f"Se cargaron {len(cuadros_gris)} cuadros del clip.")

# ==================== a) Histograma del cuadro 10 + umbralización ====================
INDICE_CUADRO_10 = 9  # "el cuadro 10" = índice 9 (0-based)
cuadro_10 = cuadros_gris[INDICE_CUADRO_10]
guardar_histograma(cuadro_10, os.path.join(CARPETA_FRAMES, "histograma_cuadro10.png"),
                    "Histograma del cuadro 10")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer_umbral = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_umbralizado.mp4"),
                                 fourcc, fps, (ancho, alto), isColor=False)

for i, cuadro in enumerate(cuadros_gris):
    _, cuadro_umbral = cv2.threshold(cuadro, VALOR_UMBRAL, 255, cv2.THRESH_BINARY)
    writer_umbral.write(cuadro_umbral)
    if i % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{i:04d}_umbralizado.png"), cuadro_umbral)

writer_umbral.release()
print(f"a) Umbralización aplicada con VALOR_UMBRAL={VALOR_UMBRAL}. "
      f"Revisa histograma_cuadro10.png; si el valle entre fondo y línea está "
      f"en otro punto, ajusta esa constante y vuelve a correr el script.")

# ==================== b) Cuadro con mínimo de línea negra ====================
conteos_negros = [int(np.sum(c < UMBRAL_NEGRO)) for c in cuadros_gris]
indice_min_linea = int(np.argmin(conteos_negros))
cuadro_referencia = cuadros_gris[indice_min_linea]

hist_referencia = guardar_histograma(
    cuadro_referencia,
    os.path.join(CARPETA_FRAMES, f"histograma_referencia_cuadro{indice_min_linea}.png"),
    f"Histograma de referencia (cuadro {indice_min_linea}, con menos línea negra)"
)
cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{indice_min_linea:04d}_referencia.png"), cuadro_referencia)

print(f"b) El cuadro con menos línea negra es el índice {indice_min_linea} "
      f"({conteos_negros[indice_min_linea]} píxeles oscuros de umbral<{UMBRAL_NEGRO}). "
      f"Su histograma queda guardado como referencia.")

# ==================== c) Especificación de histograma en los demás cuadros ====================
writer_igualado = cv2.VideoWriter(os.path.join(CARPETA_RESULTADOS, "clip_histograma_igualado.mp4"),
                                   fourcc, fps, (ancho, alto), isColor=False)

for i, cuadro in enumerate(cuadros_gris):
    if i == indice_min_linea:
        cuadro_igualado = cuadro  # el cuadro de referencia se deja igual
    else:
        cuadro_igualado = igualar_por_histograma_referencia(cuadro, hist_referencia)

    writer_igualado.write(cuadro_igualado)
    if i % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"frame_{i:04d}_igualado.png"), cuadro_igualado)

writer_igualado.release()

print("c) Especificación de histograma aplicada a todos los cuadros restantes.")
print(f"Resultados guardados en: {CARPETA_RESULTADOS}")