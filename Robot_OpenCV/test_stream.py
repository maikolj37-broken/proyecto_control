import urllib.request
import time

from camera_config import get_stream_url

URL = get_stream_url()

print("Conectando...")

inicio = time.perf_counter()

try:
    stream = urllib.request.urlopen(URL, timeout=10)
except OSError as exc:
    raise SystemExit(f"No se pudo conectar: {exc}. Revisa IP y hotspot.")

print("Conectado.")

bytes_recibidos = 0
ultimo = time.perf_counter()

try:

    while True:

        data = stream.read1(4096)

        if not data:
            print("\nEl stream terminó.")
            break

        bytes_recibidos += len(data)

        ahora = time.perf_counter()

        if ahora - ultimo >= 1.0:

            velocidad = bytes_recibidos / (ahora - inicio)

            print(
                f"Tiempo: {ahora-inicio:6.1f}s | "
                f"Datos: {bytes_recibidos/1024:8.1f} KB | "
                f"Velocidad: {velocidad/1024:6.1f} KB/s"
            )

            ultimo = ahora

except KeyboardInterrupt:

    print("\nPrueba detenida.")

except OSError as exc:
    print(f"Error de recepción: {exc}")
finally:
    stream.close()

tiempo = time.perf_counter() - inicio

print("\n==============================")
print("RESULTADO")
print("==============================")
print(f"Tiempo: {tiempo:.2f} s")
print(f"Datos: {bytes_recibidos/1024:.2f} KB")
print(f"Velocidad promedio: {(bytes_recibidos/tiempo)/1024:.2f} KB/s")
print("==============================")