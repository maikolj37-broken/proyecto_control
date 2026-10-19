"""
CONTROL 2 - Continuación del taller
Punto 2: Calcular la resta (diferencia absoluta) entre dos cuadros
consecutivos del video, tanto para el video original como para el video
modificado con gamma, y definir un criterio para decidir cuál video
"queda mejor procesado".

IMPORTANTE: reutiliza los clips en gris ya generados:
  - resultados/clip_gris.mp4              (punto 1: original en gris)
  - resultados/clip_gris_gama_<TAG>.mp4   (punto 2: gamma en gris)

CRITERIO PROPUESTO:
  Si la cámara está fija y la escena casi no cambia entre cuadros
  consecutivos, la diferencia entre cuadros consecutivos debería ser
  cercana a cero salvo donde hay movimiento real (ej. la línea que se
  desplaza). Un video con MÁS ruido produce diferencias grandes y
  dispersas por TODA la imagen (ruido aleatorio cuadro a cuadro),
  mientras que un video mejor procesado (más "limpio") debería mostrar
  diferencia baja en las zonas estáticas y diferencia concentrada solo
  en las zonas donde de verdad hay cambio.
  Por eso se reportan dos números por video:
    - diferencia_promedio: qué tan grande es el cambio en general
      (más bajo = más estable / menos ruido residual)
    - desviacion_estandar: qué tan disperso es ese cambio en la imagen
      (más bajo = el cambio está más concentrado en la línea, no
      esparcido como ruido)
  El video con menor diferencia_promedio Y menor desviación estándar
  se interpreta como el "mejor procesado" (más libre de ruido).

Salidas (en resultados/taller2/):
  - clip_diferencia_original.mp4 -> resta entre cuadros consecutivos, original
  - clip_diferencia_gamma.mp4    -> resta entre cuadros consecutivos, con gamma
  - frames_diferencia/           -> cuadros de muestra de cada resta
  - reporte impreso en consola con los números para comparar
"""

import cv2
import numpy as np
import os

# ==================== CONFIGURACIÓN ====================
CARPETA_TALLER = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes"
CARPETA_RESULTADOS = os.path.join(CARPETA_TALLER, "resultados")
CARPETA_TALLER2 = os.path.join(CARPETA_RESULTADOS, "taller2")
CARPETA_FRAMES = os.path.join(CARPETA_TALLER2, "frames_diferencia")

VIDEO_ORIGINAL = os.path.join(CARPETA_RESULTADOS, "clip_gris.mp4")

# Mismo TAG que usaste en el script de OTSU / en punto2 de gamma
GAMMA_ELEGIDA_TAG = "2_2"
VIDEO_GAMMA = os.path.join(CARPETA_RESULTADOS, f"clip_gris_gama_{GAMMA_ELEGIDA_TAG}.mp4")
# ==========================================================

os.makedirs(CARPETA_TALLER2, exist_ok=True)
os.makedirs(CARPETA_FRAMES, exist_ok=True)


def diferencia_entre_cuadros(ruta_video, nombre):
    cap = cv2.VideoCapture(ruta_video)
    if not cap.isOpened():
        raise IOError(f"No se pudo abrir: {ruta_video}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(os.path.join(CARPETA_TALLER2, f"clip_diferencia_{nombre}.mp4"),
                              fourcc, fps, (ancho, alto), isColor=False)

    ret, cuadro_anterior = cap.read()
    if not ret:
        raise IOError(f"El video {ruta_video} está vacío.")
    if len(cuadro_anterior.shape) == 3:
        cuadro_anterior = cv2.cvtColor(cuadro_anterior, cv2.COLOR_BGR2GRAY)

    promedios_por_cuadro = []
    contador = 0

    while True:
        ret, cuadro_actual = cap.read()
        if not ret:
            break
        if len(cuadro_actual.shape) == 3:
            cuadro_actual = cv2.cvtColor(cuadro_actual, cv2.COLOR_BGR2GRAY)

        diferencia = cv2.absdiff(cuadro_actual, cuadro_anterior)
        writer.write(diferencia)
        promedios_por_cuadro.append(float(np.mean(diferencia)))

        if contador % int(round(fps)) == 0:
            cv2.imwrite(os.path.join(CARPETA_FRAMES, f"{nombre}_{contador:04d}_diferencia.png"), diferencia)

        cuadro_anterior = cuadro_actual
        contador += 1

    cap.release()
    writer.release()

    diferencia_promedio = float(np.mean(promedios_por_cuadro))
    desviacion_estandar = float(np.std(promedios_por_cuadro))

    print(f"\n--- {nombre.upper()} ({contador} pares de cuadros) ---")
    print(f"Diferencia promedio entre cuadros consecutivos: {diferencia_promedio:.3f}")
    print(f"Desviación estándar de esa diferencia entre cuadros: {desviacion_estandar:.3f}")

    return diferencia_promedio, desviacion_estandar


if not os.path.exists(VIDEO_ORIGINAL):
    raise IOError(f"No existe {VIDEO_ORIGINAL}. Corre primero punto1_espacios_color.py")
if not os.path.exists(VIDEO_GAMMA):
    raise IOError(f"No existe {VIDEO_GAMMA}. Revisa GAMMA_ELEGIDA_TAG o corre primero punto2_correccion_gama.py")

prom_orig, std_orig = diferencia_entre_cuadros(VIDEO_ORIGINAL, "original")
prom_gamma, std_gamma = diferencia_entre_cuadros(VIDEO_GAMMA, "gamma")

print("\n=== COMPARACIÓN FINAL ===")
print(f"Original -> promedio={prom_orig:.3f}, desviación={std_orig:.3f}")
print(f"Gamma    -> promedio={prom_gamma:.3f}, desviación={std_gamma:.3f}")

if prom_gamma < prom_orig and std_gamma < std_orig:
    print("Según el criterio propuesto, el video CON GAMMA queda mejor procesado "
          "(menos diferencia residual y más concentrada entre cuadros).")
elif prom_orig < prom_gamma and std_orig < std_gamma:
    print("Según el criterio propuesto, el video ORIGINAL queda mejor procesado.")
else:
    print("Los resultados son mixtos (uno gana en promedio y el otro en dispersión); "
          "revisa frames_diferencia/ para decidir visualmente y justifica tu criterio en el informe.")

print(f"\nResultados guardados en: {CARPETA_TALLER2}")