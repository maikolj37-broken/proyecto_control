
import cv2
import time

# ============================================================
# CONFIGURACIÓN
# ============================================================

URL = "http://192.168.4.1:81/stream"


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
# BUCLE PRINCIPAL
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Error leyendo frame.")
        break

    # --------------------------------------------------------
    # Contador FPS
    # --------------------------------------------------------

    frame_count += 1

    elapsed = time.perf_counter() - fps_start

    if elapsed >= 1.0:

        fps = frame_count / elapsed

        frame_count = 0

        fps_start = time.perf_counter()


    # --------------------------------------------------------
    # Mostrar FPS
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"OpenCV: {fps:.1f} FPS",
        (5, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        1,
        cv2.LINE_AA
    )


    # --------------------------------------------------------
    # Mostrar imagen
    # --------------------------------------------------------

    cv2.imshow(
        "ESP32-CAM - OpenCV",
        frame
    )


    # --------------------------------------------------------
    # Teclado
    # --------------------------------------------------------

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
