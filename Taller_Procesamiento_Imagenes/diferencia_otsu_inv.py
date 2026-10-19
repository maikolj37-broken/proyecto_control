"""
CONTROL 2 - Continuación del taller
Diferencia entre el clip OTSU invertido del video con GAMMA y el clip
OTSU invertido del video ORIGINAL (los dos ya generados por
punto1_otsu.py, dentro de resultados/taller2/).

Sirve para ver, cuadro a cuadro, en qué píxeles cambia la umbralización
por efecto del gamma: donde la diferencia es 0 (negro), ambos métodos
umbralizaron igual; donde hay blanco, un video marcó ese píxel como
"línea" y el otro no.

Salidas (en resultados/taller2/):
  - clip_diferencia_otsu_inv.mp4 -> video con la diferencia absoluta cuadro a cuadro
  - frames_diferencia_otsu_inv/  -> cuadros de muestra + reporte en consola
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_TALLER2 = os.path.join(CARPETA_RESULTADOS, "taller2")
CARPETA_FRAMES = os.path.join(CARPETA_TALLER2, "frames_diferencia_otsu_inv")

VIDEO_GAMMA_OTSU_INV = os.path.join(CARPETA_TALLER2, "clip_gamma_otsu_inv.mp4")
VIDEO_ORIGINAL_OTSU_INV = os.path.join(CARPETA_TALLER2, "clip_original_otsu_inv.mp4")
# ==========================================================

os.makedirs(CARPETA_FRAMES, exist_ok=True)

for ruta in (VIDEO_GAMMA_OTSU_INV, VIDEO_ORIGINAL_OTSU_INV):
    if not os.path.exists(ruta):
        raise IOError(f"No existe {ruta}. Corre primero punto1_otsu.py")

cap_gamma = cv2.VideoCapture(VIDEO_GAMMA_OTSU_INV)
cap_original = cv2.VideoCapture(VIDEO_ORIGINAL_OTSU_INV)

fps = cap_gamma.get(cv2.CAP_PROP_FPS)
ancho = int(cap_gamma.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap_gamma.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, "clip_diferencia_otsu_inv.mp4"),
                          fourcc, fps, (ancho, alto), isColor=False)

diferencias_promedio = []
contador = 0

while True:
    ret_g, cuadro_gamma = cap_gamma.read()
    ret_o, cuadro_original = cap_original.read()
    if not ret_g or not ret_o:
        break

    if len(cuadro_gamma.shape) == 3:
        cuadro_gamma = cv2.cvtColor(cuadro_gamma, cv2.COLOR_BGR2GRAY)
    if len(cuadro_original.shape) == 3:
        cuadro_original = cv2.cvtColor(cuadro_original, cv2.COLOR_BGR2GRAY)

    diferencia = cv2.absdiff(cuadro_gamma, cuadro_original)
    writer.write(diferencia)
    diferencias_promedio.append(float(np.mean(diferencia)))

    if contador % int(round(fps)) == 0:
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_gamma_otsu_inv.png"), cuadro_gamma)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_original_otsu_inv.png"), cuadro_original)
        cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{contador:04d}_diferencia.png"), diferencia)

    contador += 1

cap_gamma.release()
cap_original.release()
writer.release()

print(f"Listo. Se compararon {contador} cuadros.")
print(f"Diferencia promedio (0-255) entre gamma-otsu_inv y original-otsu_inv: {np.mean(diferencias_promedio):.3f}")
print(f"% promedio de píxeles que cambiaron de clase entre los dos métodos: "
      f"{np.mean([d / 255 * 100 for d in diferencias_promedio]):.2f}%")
print(f"Resultados guardados en: {CARPETA_TALLER2}")