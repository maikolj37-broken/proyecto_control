import urllib.request
import time

URL = "http://192.168.4.1:81/stream"

print("Conectando...")

inicio = time.perf_counter()

stream = urllib.request.urlopen(URL, timeout=10)

print("Conectado.")

bytes_recibidos = 0
ultimo = time.perf_counter()

try:

    while True:

        data = stream.read(4096)

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

tiempo = time.perf_counter() - inicio

print("\n==============================")
print("RESULTADO")
print("==============================")
print(f"Tiempo: {tiempo:.2f} s")
print(f"Datos: {bytes_recibidos/1024:.2f} KB")
print(f"Velocidad promedio: {(bytes_recibidos/tiempo)/1024:.2f} KB/s")
print("==============================")