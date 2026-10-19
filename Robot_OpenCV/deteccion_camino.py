import cv2
import time
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL = "http://192.168.4.1:81/stream"

FRAME_WIDTH = 160
FRAME_HEIGHT = 120

# Centro de la cámara
CENTER_X = FRAME_WIDTH // 2


# ============================================================
# PARÁMETROS DEL DETECTOR
# ============================================================

# Primera fila de análisis
ROI_TOP = 68

# Última fila de análisis
ROI_BOTTOM = 116

# Separación entre scanlines
SCAN_STEP = 8

# Un píxel por debajo de este valor se considera NEGRO
BLACK_THRESHOLD = 80

# Ancho mínimo de un segmento negro
MIN_LINE_WIDTH = 4

# Ancho máximo permitido
MAX_LINE_WIDTH = 120

# Salto máximo entre centros de scanlines consecutivas
MAX_CENTER_JUMP = 35


# ============================================================
# CONECTAR A LA ESP32-CAM
# ============================================================

print("Conectando a la ESP32-CAM...")

cap = cv2.VideoCapture(URL)

if not cap.isOpened():
    print("ERROR: No se pudo abrir el stream.")
    exit()

print("Stream conectado.")
print("Iniciando OpenCV...")
print()
print("Presiona Q para salir.")


# ============================================================
# VARIABLES FPS
# ============================================================

frame_count = 0
fps = 0.0
fps_start = time.perf_counter()


# ============================================================
# FUNCIÓN:
# ENCONTRAR SEGMENTOS NEGROS EN UNA FILA
# ============================================================

def find_black_segments(row):

    """
    Busca segmentos negros consecutivos en una fila.

    Devuelve una lista con:

        (inicio, fin, centro, ancho)
    """

    black = row < BLACK_THRESHOLD

    segments = []

    start = None

    for x in range(len(black)):

        if black[x] and start is None:

            start = x

        elif not black[x] and start is not None:

            end = x - 1

            width = end - start + 1

            if MIN_LINE_WIDTH <= width <= MAX_LINE_WIDTH:

                center = (start + end) / 2

                segments.append(
                    (start, end, center, width)
                )

            start = None


    # Si la fila termina en negro
    if start is not None:

        end = len(black) - 1

        width = end - start + 1

        if MIN_LINE_WIDTH <= width <= MAX_LINE_WIDTH:

            center = (start + end) / 2

            segments.append(
                (start, end, center, width)
            )


    return segments


# ============================================================
# FUNCIÓN:
# DETECTAR CAMINO MEDIANTE SCANLINES
# ============================================================

def detect_path(gray):

    points = []

    previous_center = None


    # --------------------------------------------------------
    # Analizar varias filas
    # --------------------------------------------------------

    for y in range(
        ROI_BOTTOM,
        ROI_TOP - 1,
        -SCAN_STEP
    ):

        row = gray[y, :]

        segments = find_black_segments(row)

        if len(segments) == 0:
            continue


        # ----------------------------------------------------
        # Elegir segmento
        # ----------------------------------------------------

        best_segment = None
        best_score = float("inf")


        for segment in segments:

            start, end, center, width = segment


            # ----------------------------------------------
            # Primera detección
            # ----------------------------------------------

            if previous_center is None:

                # Preferimos segmentos cercanos al centro
                distance = abs(center - CENTER_X)

                # También favorecemos líneas razonablemente
                # anchas
                width_bonus = min(width, 40) * 0.15

                score = distance - width_bonus


            # ----------------------------------------------
            # Seguimiento de trayectoria
            # ----------------------------------------------

            else:

                distance = abs(
                    center - previous_center
                )

                # Ignorar saltos demasiado grandes
                if distance > MAX_CENTER_JUMP:

                    continue

                score = distance


            if score < best_score:

                best_score = score
                best_segment = segment


        # ----------------------------------------------------
        # Guardar punto detectado
        # ----------------------------------------------------

        if best_segment is not None:

            start, end, center, width = best_segment

            points.append(
                (y, center, start, end, width)
            )

            previous_center = center


    # ========================================================
    # COMPROBAR SI TENEMOS SUFICIENTES PUNTOS
    # ========================================================

    if len(points) < 3:

        return None, points


    # ========================================================
    # AJUSTAR UNA RECTA
    # ========================================================

    ys = np.array(
        [p[0] for p in points],
        dtype=np.float32
    )

    xs = np.array(
        [p[1] for p in points],
        dtype=np.float32
    )


    # x = pendiente*y + intercepto
    coefficients = np.polyfit(
        ys,
        xs,
        1
    )

    slope = coefficients[0]
    intercept = coefficients[1]


    # ========================================================
    # ESTIMAR CENTRO DEL CAMINO EN LA PARTE INFERIOR
    # ========================================================

    path_x = (
        slope * ROI_BOTTOM
        + intercept
    )


    path_x = int(
        np.clip(
            path_x,
            0,
            FRAME_WIDTH - 1
        )
    )


    return path_x, points


# ============================================================
# BUCLE PRINCIPAL
# ============================================================

while True:

    # --------------------------------------------------------
    # Leer frame
    # --------------------------------------------------------

    ret, frame = cap.read()

    if not ret:

        print("Error leyendo frame.")

        break


    # ========================================================
    # FPS
    # ========================================================

    frame_count += 1

    elapsed = time.perf_counter() - fps_start

    if elapsed >= 1.0:

        fps = frame_count / elapsed

        frame_count = 0

        fps_start = time.perf_counter()


    # ========================================================
    # ESCALA DE GRISES
    # ========================================================

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # ========================================================
    # DETECTAR CAMINO
    # ========================================================

    path_x, points = detect_path(gray)


    # ========================================================
    # ERROR
    # ========================================================

    if path_x is not None:

        error = path_x - CENTER_X

        path_found = True

    else:

        error = 0

        path_found = False


    # ========================================================
    # DIBUJAR ROI
    # ========================================================

    cv2.line(
        frame,
        (0, ROI_TOP),
        (FRAME_WIDTH, ROI_TOP),
        (255, 0, 255),
        1
    )


    # ========================================================
    # DIBUJAR SCANLINES Y PUNTOS DETECTADOS
    # ========================================================

    for y, center, start, end, width in points:

        # Línea horizontal donde se analizó
        cv2.line(
            frame,
            (start, y),
            (end, y),
            (0, 255, 0),
            1
        )

        # Centro del segmento
        cv2.circle(
            frame,
            (int(center), y),
            2,
            (0, 0, 255),
            -1
        )


    # ========================================================
    # DIBUJAR CENTRO DE LA CÁMARA
    # ========================================================

    cv2.line(
        frame,
        (CENTER_X, ROI_TOP),
        (CENTER_X, FRAME_HEIGHT),
        (255, 0, 0),
        1
    )


    # ========================================================
    # DIBUJAR CAMINO DETECTADO
    # ========================================================

    if path_found:

        # ----------------------------------------------------
        # Punto final estimado
        # ----------------------------------------------------

        cv2.circle(
            frame,
            (path_x, ROI_BOTTOM),
            5,
            (0, 255, 255),
            -1
        )


        # ----------------------------------------------------
        # Línea desde centro cámara al camino
        # ----------------------------------------------------

        cv2.line(
            frame,
            (CENTER_X, ROI_BOTTOM),
            (path_x, ROI_BOTTOM),
            (0, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Dibujar trayectoria estimada
        # ----------------------------------------------------

        if len(points) >= 2:

            ys = np.array(
                [p[0] for p in points],
                dtype=np.float32
            )

            xs = np.array(
                [p[1] for p in points],
                dtype=np.float32
            )

            coefficients = np.polyfit(
                ys,
                xs,
                1
            )

            slope = coefficients[0]
            intercept = coefficients[1]


            x1 = int(
                slope * ROI_TOP
                + intercept
            )

            x2 = int(
                slope * ROI_BOTTOM
                + intercept
            )

            x1 = np.clip(
                x1,
                0,
                FRAME_WIDTH - 1
            )

            x2 = np.clip(
                x2,
                0,
                FRAME_WIDTH - 1
            )


            cv2.line(
                frame,
                (x1, ROI_TOP),
                (x2, ROI_BOTTOM),
                (0, 255, 255),
                2
            )


    # ========================================================
    # INFORMACIÓN
    # ========================================================

    if path_found:

        status = "CAMINO OK"

        if error < -5:

            direction = "IZQUIERDA"

        elif error > 5:

            direction = "DERECHA"

        else:

            direction = "CENTRADO"


    else:

        status = "SIN CAMINO"

        direction = "---"


    # ========================================================
    # TEXTO
    # ========================================================

    cv2.putText(
        frame,
        status,
        (3, 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (0, 255, 0) if path_found else (0, 0, 255),
        1,
        cv2.LINE_AA
    )


    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (105, 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (0, 255, 0),
        1,
        cv2.LINE_AA
    )


    cv2.putText(
        frame,
        f"Error: {error:+d}px",
        (3, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (0, 255, 255),
        1,
        cv2.LINE_AA
    )


    cv2.putText(
        frame,
        f"Centro: {path_x if path_found else '--'}",
        (3, 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )


    cv2.putText(
        frame,
        f"Dir: {direction}",
        (3, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )


    # ========================================================
    # MOSTRAR
    # ========================================================

    cv2.imshow(
        "ESP32-CAM - Deteccion de Camino",
        frame
    )


    # ========================================================
    # TECLADO
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# ============================================================
# CERRAR
# ============================================================

cap.release()

cv2.destroyAllWindows()

print()
print("Programa terminado.")