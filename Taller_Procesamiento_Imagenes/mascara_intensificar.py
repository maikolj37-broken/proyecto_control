"""
CONTROL 2 - Continuación del taller
Construir una MÁSCARA a partir de clip_diferencia_otsu_inv.mp4 y
multiplicarla por el video con gamma, para:
  - eliminar el ruido alrededor del camino (queda en negro)
  - conservar / intensificar la línea

Pipeline:
  1) Umbralizar la diferencia (OTSU) -> máscara binaria (0 / 255)
  2) Limpiar la máscara con apertura morfológica (quita motas de ruido)
  3) (Opcional) Dilatar un poco para cubrir bien el ancho de la línea
  4) Normalizar la máscara a [0, 1]
  5) Multiplicar la máscara por el video en gris que quieres intensificar
  6) (Opcional) Aplicar una ganancia > 1 para que la línea quede más intensa

Salidas (en resultados/taller2/):
  - mascara.mp4               -> la máscara binaria ya limpiada (para ver qué está dejando pasar)
  - clip_resultado_mascara.mp4 -> el video final: ruido eliminado, línea intensificada
  - frames_mascara/            -> cuadros de muestra de cada etapa
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_TALLER2 = os.path.join(CARPETA_RESULTADOS, "taller2")
CARPETA_FRAMES = os.path.join(CARPETA_TALLER2, "frames_mascara")

VIDEO_DIFERENCIA = os.path.join(CARPETA_TALLER2, "clip_diferencia_otsu_inv.mp4")

# Video al que se le va a aplicar la máscara (el que quieres "limpiar" /
# intensificar). Por defecto el video en gris con el gamma elegido.
VIDEO_A_INTENSIFICAR = os.path.join(CARPETA_RESULTADOS, "clip_gris_gama_2_2.mp4")

# Si True, usa OTSU automático para umbralizar la diferencia.
# Si False, usa el valor fijo de UMBRAL_MASCARA_MANUAL.
USAR_OTSU_PARA_MASCARA = True
UMBRAL_MASCARA_MANUAL = 30

TAMANO_KERNEL_APERTURA = 3   # limpia motas de ruido pequeñas (impar)
APLICAR_DILATACION = True
TAMANO_KERNEL_DILATACION = 3

GANANCIA = 1.3  # >1 intensifica la línea; deja en 1.0 para no amplificar
# ==========================================================

os.makedirs(CARPETA_TALLER2, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)

for ruta in (VIDEO_DIFERENCIA, VIDEO_A_INTENSIFICAR):
    if not os.path.exists(ruta):
        raise IOError(f"No existe {ruta}. Verifica que ya corriste los scripts anteriores.")

cap_diff = cv2.VideoCapture(VIDEO_DIFERENCIA)
cap_video = cv2.VideoCapture(VIDEO_A_INTENSIFICAR)

fps = cap_diff.get(cv2.CAP_PROP_FPS)
ancho = int(cap_diff.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap_diff.get(cv2.CAP_PROP_FRAME_HEIGHT))

kernel_apertura = np.ones((TAMANO_KERNEL_APERTURA, TAMANO_KERNEL_APERTURA), np.uint8)
kernel_dilatacion = np.ones((TAMANO_KERNEL_DILATACION, TAMANO_KERNEL_DILATACION), np.uint8)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer_mascara = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, "mascara.mp4"),
                                  fourcc, fps, (ancho, alto), isColor=False)
writer_resultado = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, "clip_resultado_mascara.mp4"),
                                    fourcc, fps, (ancho, alto), isColor=False)

contador = 0
while True:
    ret_d, cuadro_diff = cap_diff.read()
    ret_v, cuadro_video = cap_video.read()
    if not ret_d or not ret_v:
        break

    if len(cuadro_diff.shape) == 3:
        cuadro_diff = cv2.cvtColor(cuadro_diff, cv2.COLOR_BGR2GRAY)
    if len(cuadro_video.shape) == 3:
        cuadro_video = cv2.cvtColor(cuadro_video, cv2.COLOR_BGR2GRAY)

    # 1) Umbralizar la diferencia -> máscara binaria
    if USAR_OTSU_PARA_MASCARA:
        _, mascara = cv2.threshold(cuadro_diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, mascara = cv2.threshold(cuadro_diff, UMBRAL_MASCARA_MANUAL, 255, cv2.THRESH_BINARY)

    # 2) Limpiar ruido pequeño con apertura morfológica
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel_apertura)

    # 3) Dilatar un poco para cubrir bien el ancho de la línea (opcional)
    if APLICAR_DILATACION:
        mascara = cv2.dilate(mascara, kernel_dilatacion)

    # 4) Normalizar a [0, 1]
    mascara_normalizada = mascara.astype(np.float32) / 255.0

    # 5) Multiplicar la máscara por el video a intensificar
    resultado = cuadro_video.astype(np.float32) * mascara_normalizada

    # 6) Ganancia opcional para intensificar la línea
    resultado = resultado * GANANCIA
    resultado = np.clip(resultado, 0, 255).astype(np.uint8)

    writer_mascara.write(mascara)
    writer_resultado.write(resultado)

    if contador % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_diferencia.png"), cuadro_diff)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_mascara.png"), mascara)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_video_original.png"), cuadro_video)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_resultado.png"), resultado)

    contador += 1

cap_diff.release()
cap_video.release()
writer_mascara.release()
writer_resultado.release()

print(f"Listo. Se procesaron {contador} cuadros.")
print(f"Resultados guardados en: {CARPETA_TALLER2}")
print("Revisa frames_mascara/: compara *_video_original vs *_resultado para ver si el ruido")
print("alrededor del camino desapareció y la línea quedó más intensa.")
print("Si sobra ruido: sube TAMANO_KERNEL_APERTURA. Si la línea se rompe: bájalo o quita la dilatación.")