# Verificaciones de la entrega — 19 de octubre de 2026

## Firmware nuevo

Compilación con Arduino CLI, Arduino-ESP32 **3.3.12**, FQBN **esp32:esp32:esp32cam**, salida **0**.

```
Sketch uses 1016297 bytes (32%) of program storage space. Maximum is 3145728 bytes.
Global variables use 57632 bytes (17%) of dynamic memory, leaving 270048 bytes for local variables. Maximum is 327680 bytes.
```

No se ha cargado el firmware ni comprobado alimentación, sensor, orientación, stream o FPS en hardware. La compilación demuestra compatibilidad del código con la placa seleccionada; no sustituye el ensayo físico.

## Python y talleres

- 30 scripts Python del repositorio analizados con `ast.parse`: sin errores de sintaxis.
- `python -B validar_taller_opencv3.py`, ejecutado desde `Taller_Procesamiento_Imagenes`: salida **0**.
- Resultado: `OK: ajuste L2 vertical/inclinado/sin datos, centros, anchos, perdida/corte, signo PWM, desplazamiento y reconstruccion Fourier.`
- Entorno usado: Python 3.14.7, OpenCV 5.0.0 y NumPy 2.5.1.
- Estos ensayos no ejecutan los cuatro programas contra la cámara real ni validan los controladores históricos en motores.

## Copias

1105 archivos de origen copiados (aproximadamente 283.4 MiB), comparados byte a byte mediante SHA-256 durante la copia. Se omiten 28 entradas de caché, temporales, ZIP o archivos vacíos, detalladas en `exclusiones.csv`. El inventario describe el material de origen; las nuevas guías y archivos de configuración del repositorio se añadieron después.
