import cv2
import numpy as np
import os


# ============================================================
# RUTAS
# ============================================================

INPUT_VIDEO = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes\resultados\taller2\clip_diferencia_otsu_inv.mp4"

OUTPUT_DIR = r"C:\Users\Usuario\Desktop\Taller_Procesamiento_Imagenes\resultados\taller2"

OUTPUT_VIDEO = os.path.join(
    OUTPUT_DIR,
    "clip_diferencia_otsu_inv_sin_ruido.mp4"
)


# ============================================================
# PARAMETROS
# ============================================================

# Tamaño del filtro para eliminar ruido pequeño
# NO poner un valor demasiado grande porque podría borrar el camino.
KERNEL_APERTURA = 3

# Tamaño del cierre para unir pequeñas interrupciones
KERNEL_CIERRE = 3

# Área mínima de una región blanca.
# Si una región tiene menos píxeles que esto,
# se considera ruido.
AREA_MINIMA = 80


# ============================================================
# CREAR CARPETAS SI NO EXISTEN
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# ABRIR VIDEO
# ============================================================

cap = cv2.VideoCapture(INPUT_VIDEO)

if not cap.isOpened():
    print("ERROR: No se pudo abrir el video.")
    print(INPUT_VIDEO)
    exit()


# ============================================================
# INFORMACION DEL VIDEO
# ============================================================

fps = cap.get(cv2.CAP_PROP_FPS)
ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
numero_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print("=" * 60)
print("        ELIMINACION DE RUIDO")
print("=" * 60)
print(f"Video de entrada: {INPUT_VIDEO}")
print(f"Resolucion: {ancho} x {alto}")
print(f"FPS: {fps}")
print(f"Cuadros: {numero_frames}")
print("=" * 60)


# ============================================================
# CONFIGURAR VIDEO DE SALIDA
# ============================================================

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

out = cv2.VideoWriter(
    OUTPUT_VIDEO,
    fourcc,
    fps,
    (ancho, alto),
    False
)

if not out.isOpened():
    print("ERROR: No se pudo crear el video de salida.")
    cap.release()
    exit()


# ============================================================
# KERNELS MORFOLOGICOS
# ============================================================

kernel_apertura = cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE,
    (KERNEL_APERTURA, KERNEL_APERTURA)
)

kernel_cierre = cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE,
    (KERNEL_CIERRE, KERNEL_CIERRE)
)


# ============================================================
# PROCESAMIENTO
# ============================================================

frame_actual = 0

while True:

    ret, frame = cap.read()

    if not ret:
        break

    frame_actual += 1

    # --------------------------------------------------------
    # 1. Convertir a escala de grises
    # --------------------------------------------------------

    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame.copy()


    # --------------------------------------------------------
    # 2. Asegurar imagen binaria
    # --------------------------------------------------------
    # Todo lo que sea blanco queda en 255
    # Todo lo demás queda en 0.
    # --------------------------------------------------------

    _, binary = cv2.threshold(
        gray,
        127,
        255,
        cv2.THRESH_BINARY
    )


    # --------------------------------------------------------
    # 3. APERTURA MORFOLOGICA
    # --------------------------------------------------------
    # Elimina pequeñas partículas blancas aisladas.
    #
    # IMPORTANTE:
    # usamos 3x3 para no destruir el camino.
    # --------------------------------------------------------

    clean = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel_apertura
    )


    # --------------------------------------------------------
    # 4. BUSCAR COMPONENTES CONECTADOS
    # --------------------------------------------------------
    # Cada región blanca independiente se analiza.
    # --------------------------------------------------------

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        clean,
        connectivity=8
    )


    # Crear imagen completamente negra
    resultado = np.zeros_like(clean)


    # --------------------------------------------------------
    # 5. ELIMINAR COMPONENTES MUY PEQUEÑOS
    # --------------------------------------------------------

    for i in range(1, num_labels):

        area = stats[i, cv2.CC_STAT_AREA]

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]


        # ----------------------------------------------------
        # Criterio principal:
        # conservar regiones suficientemente grandes.
        # ----------------------------------------------------

        if area >= AREA_MINIMA:

            resultado[labels == i] = 255


    # --------------------------------------------------------
    # 6. CIERRE MORFOLOGICO SUAVE
    # --------------------------------------------------------
    # Ayuda a unir pequeñas interrupciones del camino.
    # --------------------------------------------------------

    resultado = cv2.morphologyEx(
        resultado,
        cv2.MORPH_CLOSE,
        kernel_cierre
    )


    # --------------------------------------------------------
    # 7. GUARDAR CUADRO
    # --------------------------------------------------------

    out.write(resultado)


    # Mostrar progreso
    if frame_actual % 30 == 0:

        porcentaje = (frame_actual / numero_frames) * 100

        print(
            f"Procesando: {frame_actual}/{numero_frames} "
            f"({porcentaje:.1f}%)"
        )


# ============================================================
# FINALIZAR
# ============================================================

cap.release()
out.release()

cv2.destroyAllWindows()


print()
print("=" * 60)
print("       PROCESAMIENTO TERMINADO")
print("=" * 60)
print("Video generado:")
print(OUTPUT_VIDEO)
print("=" * 60)