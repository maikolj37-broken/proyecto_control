import cv2
import urllib.request
import numpy as np
import time

URL = "http://192.168.4.1:81/stream"

print("Conectando al ESP32-CAM...")
inicio_conexion = time.perf_counter()

stream = urllib.request.urlopen(URL, timeout=10)

tiempo_conexion = time.perf_counter() - inicio_conexion

print(f"Conexión establecida en: {tiempo_conexion:.3f} s")
print("Iniciando prueba...")
print("Presiona Q para terminar.\n")

buffer = b""

frames = 0
frames_validos = 0

inicio = time.perf_counter()
ultimo_frame = inicio

fps_actual = 0
latencia_frame = 0

ultimo_timestamp = None
intervalos = []

while True:

    try:
        data = stream.read(4096)

        if not data:
            print("ERROR: el stream dejó de enviar datos.")
            break

        buffer += data

        while True:

            inicio_jpg = buffer.find(b"\xff\xd8")

            if inicio_jpg == -1:
                # Evitar que el buffer crezca indefinidamente
                if len(buffer) > 100000:
                    buffer = buffer[-10000:]
                break

            fin_jpg = buffer.find(b"\xff\xd9", inicio_jpg + 2)

            if fin_jpg == -1:
                break

            jpg = buffer[inicio_jpg:fin_jpg + 2]

            buffer = buffer[fin_jpg + 2:]

            frame = cv2.imdecode(
                np.frombuffer(jpg, dtype=np.uint8),
                cv2.IMREAD_COLOR
            )

            if frame is None:
                continue

            ahora = time.perf_counter()

            frames += 1
            frames_validos += 1

            # Tiempo entre frames
            intervalo = ahora - ultimo_frame
            ultimo_frame = ahora

            if intervalo > 0:
                intervalos.append(intervalo)

            # FPS instantáneo
            fps_actual = 1.0 / intervalo if intervalo > 0 else 0

            # Mostrar información
            alto, ancho = frame.shape[:2]

            texto1 = f"FPS: {fps_actual:.1f}"
            texto2 = f"Frame: {frames_validos}"
            texto3 = f"Buffer: {len(buffer)/1024:.1f} KB"
            texto4 = f"JPEG: {len(jpg)/1024:.1f} KB"

            cv2.putText(
                frame,
                texto1,
                (5, 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1
            )

            cv2.putText(
                frame,
                texto2,
                (5, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1
            )

            cv2.putText(
                frame,
                texto3,
                (5, 49),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1
            )

            cv2.putText(
                frame,
                texto4,
                (5, 66),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 0),
                1
            )

            cv2.imshow("ESP32-CAM - Prueba FPS", frame)

            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord('q'):
                raise KeyboardInterrupt

            # Solo procesamos un frame antes de volver a leer
            break

    except KeyboardInterrupt:
        break

    except Exception as e:
        print("Error:", e)
        break


# ==========================
# RESULTADOS
# ==========================

tiempo_total = time.perf_counter() - inicio

cv2.destroyAllWindows()

print("\n==============================")
print("      RESULTADOS")
print("==============================")

print(f"Tiempo de prueba: {tiempo_total:.2f} s")
print(f"Frames recibidos: {frames_validos}")

if tiempo_total > 0:
    fps_promedio = frames_validos / tiempo_total
    print(f"FPS promedio: {fps_promedio:.2f}")

if len(intervalos) > 0:

    promedio_intervalo = sum(intervalos) / len(intervalos)

    print(
        f"Intervalo promedio: "
        f"{promedio_intervalo * 1000:.2f} ms"
    )

    print(
        f"FPS calculado por intervalo: "
        f"{1 / promedio_intervalo:.2f}"
    )

    intervalo_max = max(intervalos)

    print(
        f"Mayor pausa entre frames: "
        f"{intervalo_max:.2f} s"
    )

    if intervalo_max > 1:
        print("⚠️ Se detectó un congelamiento superior a 1 segundo.")

    elif intervalo_max > 0.5:
        print("⚠️ Se detectó una pausa importante.")

    elif intervalo_max > 0.2:
        print("⚠️ Hay pequeños congelamientos.")

    else:
        print("✓ No se detectaron congelamientos importantes.")

print("==============================")