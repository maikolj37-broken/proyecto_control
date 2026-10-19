# Proyecto de control: robot diferencial y visión

Avance del proyecto al 19 de octubre de 2026. Se reúnen los programas existentes de motores y encoders, las pruebas de cámara en Python y los talleres de procesamiento de imágenes.

## Contenido

| Carpeta | Contenido |
|---|---|
| `arduino/` | Calibración, PWM, identificación, ensayos por WiFi, control RST y firmware de cámara. Cada carpeta con `.ino` es un programa independiente. |
| `arduino/identificacion/` | Scripts MATLAB existentes; requieren los CSV de ensayo mencionados en cada script, no encontrados en las carpetas entregadas. |
| `Robot_OpenCV/` | Conexión MJPEG, visualización, medición de recepción y detección de camino. |
| `Taller_Procesamiento_Imagenes/` | Talleres y resultados históricos usando videos de referencia ajenos a nuestra cámara. |
| `docs/` | Guía de prueba, inventario SHA-256 de las copias y exclusiones. |

## Prueba de la cámara

La nueva carpeta `arduino/camara_opencv/` contiene el firmware para **ESP32-CAM AI Thinker con OV3660**, red `RobotCam`, clave de demostración `robotcam123`, video MJPEG en `http://192.168.4.1:81/stream`, resolución 160 × 120. Los cuatro programas originales de `Robot_OpenCV` ya usan esa URL.

Consulta [la guía de carga y prueba](docs/PRUEBA_CAMARA.md).

```powershell
cd Robot_OpenCV
python -m pip install -r requirements.txt
python camera_test.py
# Cerrar el programa anterior antes del siguiente:
python deteccion_camino.py
```

## Alcance y estado

- El firmware de cámara transmite imágenes; no envía instrucciones a motores.
- La detección en Python y el control de motores aún no están integrados en un lazo cerrado por visión.
- Los resultados de los talleres corresponden a videos de referencia, no a capturas de la OV3660 del robot. El PWM del taller es una propuesta offline y no una validación física.
- `test_fps_latency.py` mide recepción e intervalos entre imágenes. No mide latencia física extremo a extremo entre exposición y pantalla.
- La compilación y verificaciones de esta entrega se registran en [VALIDACION.md](docs/VALIDACION.md). La carga, orientación, alimentación y video real requieren ensayo con la placa.
- Los programas históricos se conservan sin cambiar sus parámetros. No se afirma que todos compilen con la misma versión de Arduino-ESP32.

## Talleres

Desde `Taller_Procesamiento_Imagenes`, instalar `requisitos_taller_opencv3.txt` y seguir `PASO_A_PASO_TALLER_OPENCV3.md`. Se preservan también versiones anteriores y sus resultados. Los archivos grandes generados hacen que la primera descarga sea considerable.

## Procedencia

Copias de las carpetas locales de Arduino `proyecto_control`, `Robot_OpenCV` y `Taller_Procesamiento_Imagenes`. `docs/inventario.csv` registra la ruta de destino, tamaño y SHA-256 de cada archivo copiado. `docs/exclusiones.csv` identifica archivos comprimidos, cachés, temporales y vacíos omitidos. Los originales permanecen en su ubicación; la única adición al árbol original de Arduino es `camara_opencv` y se añaden instrucciones/dependencias al árbol de OpenCV.

Las claves WiFi incluidas son las claves locales de demostración de los sketches. No son credenciales de una red doméstica. Los videos de referencia se conservan como material de estudio; no se atribuye su captura al equipo ni se concede una licencia sobre contenido de terceros.

Referencia técnica del firmware: [controlador esp32-camera de Espressif](https://github.com/espressif/esp32-camera) y ejemplo CameraWebServer de Arduino-ESP32 3.3.12 instalado localmente.
