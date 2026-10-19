# Verificaciones de la entrega — 19 de octubre de 2026

## Firmware inicial (histórico, anterior al cambio a STA)

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

## Copias iniciales (histórico)

1105 archivos de origen copiados (aproximadamente 283.4 MiB), comparados byte a byte mediante SHA-256 durante la copia. Se omiten 28 entradas de caché, temporales, ZIP o archivos vacíos, detalladas en `exclusiones.csv`. El inventario describe el material de origen; las nuevas guías y archivos de configuración del repositorio se añadieron después.


## Actualización STA y clientes OpenCV

El firmware actualizado del usuario utiliza hotspot, IP por DHCP, MJPEG en el puerto 81, VGA/QVGA y rotación de 180 grados. Se conserva su funcionamiento; los datos WiFi se extraen a `secrets.h` local, ignorado por Git, con plantilla `secrets.example.h` para otras máquinas.

- `python -m unittest discover -s tests -v`: 3 pruebas aprobadas (salida 0). Incluyen URL/configuración, escala/orientación y ejecución de los cuatro clientes contra un servidor HTTP MJPEG local en VGA y QVGA (8 ejecuciones).
- Las ventanas se simulan en las pruebas, pero la recepción HTTP y la decodificación JPEG/OpenCV son reales. El servidor termina intencionalmente: los avisos FFmpeg de fin prematuro corresponden a ese cierre de prueba.
- Sintaxis de los 5 módulos Python revisada y `--help` de los cuatro programas con salida 0.
- `camera_test.py` conserva resolución de entrada; `deteccion_camino.py` reduce a 160 × 120 antes de analizar, sin duplicar la rotación del firmware.
- La prueba de FPS procesa todos los JPEG completos disponibles; no mide latencia física de captura.
- No se ha comprobado esta versión contra la placa física, ni medido FPS reales, conexión del hotspot o detección sobre la pista del robot.

Compilación del firmware STA actual: Arduino-ESP32 3.3.12, `esp32:esp32:esp32cam`, salida 0. Programa: 1027389 bytes (32%); variables globales: 59352 bytes (18%).

## Taller en vivo y anticipación espacial FFT

- Se agregan `seguimiento_linea.py`, `linea_pipeline.py`, `linea_fft.py` y `linea_taller.py` en Robot_OpenCV. No cambian los firmwares ni los clientes anteriores.
- 11 pruebas automáticas aprobadas con `python -m unittest discover -s tests -v` (salida 0). Se comprueban reutilización exacta de las funciones del taller, recta, desplazamientos laterales, curvas izquierda/derecha, pérdida/recuperación, ausencia de cobertura lejana, línea blanca/manual, filtrado FFT y ejecución del programa nuevo contra un servidor HTTP MJPEG local (8 cuadros procesados).
- Ensayo de integración por CLI con video **sintético** de 90 cuadros: curva derecha, 15 cuadros sin línea, curva izquierda. CSV de 91 filas incluyendo finalización: guía válida en curvas, velocidad relativa cero durante pérdida y al finalizar. No es un ensayo del robot.
- Panel de 16 etapas renderizado e inspeccionado visualmente; ejemplo sintético disponible en `docs/imagenes/seguimiento_ejemplo_sintetico.png`.
- Consulta a `/status` en la última IP indicada por el usuario sin respuesta dentro de 3 segundos. No se pudo verificar esta nueva versión contra la cámara durante esta entrega.
- La FFT filtra el perfil espacial observado; no pronostica tramos fuera de imagen ni estima velocidad física. Las referencias son adimensionales y requieren calibración/integración con el controlador de motores antes de accionar el robot.
