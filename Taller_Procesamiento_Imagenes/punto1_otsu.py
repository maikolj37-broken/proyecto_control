"""
CONTROL 2 - Continuación del taller
Punto 1: Umbralización con OTSU (binary y binary_inverse) sobre el video
original y sobre el video ya modificado con gamma (el que obtuviste en el
punto 2 de ayer). Compara esos resultados contra una umbralización manual
usando el mejor valor que tú elijas a partir del histograma.

IMPORTANTE: este script NO vuelve a leer el video crudo (ideal.mp4).
Reutiliza los clips en escala de grises que ya generaste:
  - resultados/clip_gris.mp4              (punto 1: original en gris)
  - resultados/clip_gris_gama_<TAG>.mp4   (punto 2: gamma en gris)

Salidas (en resultados/taller2/):
  - clip_original_otsu_binary.mp4 / clip_original_otsu_inv.mp4 / clip_original_manual.mp4
  - clip_gamma_otsu_binary.mp4    / clip_gamma_otsu_inv.mp4    / clip_gamma_manual.mp4
  - frames_otsu/ -> cuadros de muestra de las 6 versiones + reporte en consola
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_TALLER2 = os.path.join(CARPETA_RESULTADOS, "taller2")
CARPETA_FRAMES = os.path.join(CARPETA_TALLER2, "frames_otsu")

VIDEO_ORIGINAL = os.path.join(CARPETA_RESULTADOS, "clip_gris.mp4")

# Pon aquí el mismo TAG que usaste en punto2 para el gamma que elegiste
# como "el mejor" (ej: gamma 0.7 -> archivo clip_gris_gama_0_7.mp4)
GAMMA_ELEGIDA_TAG = "2_2"
VIDEO_GAMMA = os.path.join(CARPETA_RESULTADOS, f"clip_gris_gama_{GAMMA_ELEGIDA_TAG}.mp4")

# Umbral manual "elegido a ojo" a partir del histograma (ajusta según lo
# que veas en frames_punto5/histograma_cuadro10.png del punto 5 anterior)
UMBRAL_MANUAL_ORIGINAL = 80
UMBRAL_MANUAL_GAMMA = 80
# ==========================================================

os.makedirs(CARPETA_TALLER2, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)


def procesar_video(ruta_video, nombre, umbral_manual):
    cap = cv2.VideoCapture(ruta_video)
    if not cap.isOpened():
        raise IOError(f"No se pudo abrir: {ruta_video}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w_bin = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, f"clip_{nombre}_otsu_binary.mp4"),
                             fourcc, fps, (ancho, alto), isColor=False)
    w_inv = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, f"clip_{nombre}_otsu_inv.mp4"),
                             fourcc, fps, (ancho, alto), isColor=False)
    w_manual = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, f"clip_{nombre}_manual.mp4"),
                                fourcc, fps, (ancho, alto), isColor=False)

    valores_otsu = []
    porcentaje_blanco_otsu = []
    porcentaje_blanco_manual = []

    contador = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # OTSU calcula automáticamente el mejor umbral global del cuadro
        valor_otsu, binaria = cv2.threshold(frame, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, inversa = cv2.threshold(frame, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        _, manual = cv2.threshold(frame, umbral_manual, 255, cv2.THRESH_BINARY)

        w_bin.write(binaria)
        w_inv.write(inversa)
        w_manual.write(manual)

        valores_otsu.append(valor_otsu)
        porcentaje_blanco_otsu.append(np.mean(binaria == 255) * 100)
        porcentaje_blanco_manual.append(np.mean(manual == 255) * 100)

        if contador % int(round(fps)) == 0:
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{nombre}_{contador:04d}_original.png"), frame)
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{nombre}_{contador:04d}_otsu_binary.png"), binaria)
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{nombre}_{contador:04d}_otsu_inv.png"), inversa)
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{nombre}_{contador:04d}_manual.png"), manual)

        contador += 1

    cap.release()
    w_bin.release()
    w_inv.release()
    w_manual.release()

    print(f"\n--- {nombre.upper()} ({contador} cuadros) ---")
    print(f"Umbral OTSU: promedio={np.mean(valores_otsu):.1f}  min={np.min(valores_otsu):.1f}  max={np.max(valores_otsu):.1f}")
    print(f"Umbral manual usado: {umbral_manual}")
    print(f"% de píxeles blancos con OTSU (binary):   {np.mean(porcentaje_blanco_otsu):.2f}%")
    print(f"% de píxeles blancos con umbral manual:   {np.mean(porcentaje_blanco_manual):.2f}%")


if not os.path.exists(VIDEO_ORIGINAL):
    raise IOError(f"No existe {VIDEO_ORIGINAL}. Corre primero punto1_espacios_color.py")
if not os.path.exists(VIDEO_GAMMA):
    raise IOError(f"No existe {VIDEO_GAMMA}. Revisa GAMMA_ELEGIDA_TAG o corre primero punto2_correccion_gama.py")

procesar_video(VIDEO_ORIGINAL, "original", UMBRAL_MANUAL_ORIGINAL)
procesar_video(VIDEO_GAMMA, "gamma", UMBRAL_MANUAL_GAMMA)

print(f"\nResultados guardados en: {CARPETA_TALLER2}")
print("Para tu opinión: compara visualmente frames_otsu/*_otsu_binary vs *_manual, y usa el")
print("umbral OTSU promedio como referencia objetiva de qué tan cerca estaba tu umbral manual.")
print("Un umbral OTSU más 'estable' (min y max cercanos) en el video con gamma vs el original,")
print("es un indicio de que el ajuste de gamma facilita la umbralización automática.")