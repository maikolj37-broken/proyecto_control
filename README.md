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

La carpeta `arduino/camara_opencv/` contiene el firmware actualizado para **ESP32-CAM AI Thinker con OV3660**. Se conecta al hotspot en modo STA: **no crea una red RobotCam**. El monitor serie muestra la IP asignada. Transmite MJPEG en `http://IP:81/stream`, a VGA (640 × 480) con PSRAM o QVGA (320 × 240) sin ella. El firmware ya gira la imagen 180 grados.

Antes de compilar una descarga de GitHub, copiar `secrets.example.h` como `secrets.h` y completar los datos del hotspot. El archivo real queda excluido de Git. Los cuatro clientes aceptan `--ip`, `--url` o la variable `ROBOT_CAMERA_IP`; sin esos argumentos preguntan la IP al iniciar. El detector reduce a 160 × 120 para conservar su ROI y umbrales; los visores conservan la resolución recibida.

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
- Los programas históricos de motores y talleres se conservan sin cambiar sus parámetros. No se afirma que todos compilen con la misma versión de Arduino-ESP32.

## Talleres

### Taller aplicado al stream y anticipación FFT

Desde `Robot_OpenCV`, ejecutar `python seguimiento_linea.py --ip IP_DE_LA_CAMARA`.
El nuevo programa muestra 16 etapas, reutiliza el ajuste L2 del taller y filtra por FFT el perfil de centros para anticipar la dirección de la pista **visible**. Produce error lateral y referencias adimensionales para un futuro controlador; todavía no envía órdenes a motores. Consulta [el procedimiento paso a paso](Robot_OpenCV/SEGUIMIENTO_PASO_A_PASO.md).

Teclas: M mosaico, N/P etapas, Espacio pausa, S guardar imágenes, Q salir. `--guardar` registra mediciones. Los resultados de estas nuevas sesiones se guardan localmente y se excluyen de Git.

Desde `Taller_Procesamiento_Imagenes`, instalar `requisitos_taller_opencv3.txt` y seguir `PASO_A_PASO_TALLER_OPENCV3.md`. Se preservan también versiones anteriores y sus resultados. Los archivos grandes generados hacen que la primera descarga sea considerable.

## Procedencia

Copias de las carpetas locales de Arduino `proyecto_control`, `Robot_OpenCV` y `Taller_Procesamiento_Imagenes`. `docs/inventario.csv` conserva el inventario de la copia inicial (rutas, tamaños y SHA-256); las modificaciones posteriores se consultan en el historial Git. `docs/exclusiones.csv` identifica archivos comprimidos, cachés, temporales y vacíos omitidos. Los originales permanecen en su ubicación; la única adición al árbol original de Arduino es `camara_opencv` y se añaden instrucciones/dependencias al árbol de OpenCV.

Las claves publicadas de los sketches históricos de motores son de demostración. Los datos reales del hotspot de la cámara se guardan únicamente en `secrets.h`, excluido de Git. Los videos de referencia se conservan como material de estudio; no se atribuye su captura al equipo ni se concede una licencia sobre contenido de terceros.

Referencia técnica del firmware: [controlador esp32-camera de Espressif](https://github.com/espressif/esp32-camera) y ejemplo CameraWebServer de Arduino-ESP32 3.3.12 instalado localmente.
