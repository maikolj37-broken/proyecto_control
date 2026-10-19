# Prueba de cámara: firmware STA y clientes OpenCV

## Firmware actual

ESP32-CAM AI Thinker con OV3660. Se conecta al hotspot configurado en `secrets.h`; **no crea RobotCam**. El monitor serie a 115200 muestra `Direccion IP`, RSSI y `Servidor iniciado`.

- Página de video: `http://IP/` (puerto 80).
- Estado JSON: `http://IP/status` (`fps`, `frames`, `resolution`).
- Video MJPEG: `http://IP:81/stream`.
- Con PSRAM: VGA, 640 × 480. Sin PSRAM: QVGA, 320 × 240.
- La imagen ya está girada 180 grados en el firmware; Python no vuelve a girarla.

## Cargar

1. Abrir `camara_opencv.ino`. Si se descargó desde GitHub, copiar `secrets.example.h` a `secrets.h` y escribir allí el nombre y la clave del hotspot. La copia local de Arduino ya conserva los datos del usuario. No subir `secrets.h` a GitHub.
2. Elegir **AI Thinker ESP32-CAM**, paquete **esp32 by Espressif Systems 3.3.12**, y el puerto de la placa.
3. Usar alimentación estable por 5V/GND y UART de nivel 3.3V. Si se utilizó puente GPIO0–GND para cargar, retirarlo antes de reiniciar en modo normal. Con ESP32-CAM-MB, seguir el procedimiento de la base.
4. Activar el hotspot en 2.4 GHz, cargar y reiniciar. Abrir el monitor serie a 115200.
5. Anotar la IP mostrada; puede cambiar al reconectar. Si aparece `Error camara` o `Error conectando a WiFi`, resolver ese error antes de iniciar Python. El firmware espera hasta 20 segundos por WiFi y no inicia los servidores si falla.

## Conectar y ejecutar

Conectar el computador al mismo hotspot. Desde `Robot_OpenCV`:

```powershell
python -m pip install -r requirements.txt
python camera_test.py
```

El programa pregunta la IP de la cámara. También se puede pasar directamente; **192.168.43.25 es solo un ejemplo**, sustituir por la IP del monitor serie:

```powershell
python camera_test.py --ip 192.168.43.25
python deteccion_camino.py --ip 192.168.43.25
python test_fps_latency.py --ip 192.168.43.25
python test_stream.py --ip 192.168.43.25
```

Ejecutar **solo uno a la vez**. Cerrar la página de video del navegador antes de usar Python: el firmware atiende un cliente de streaming a la vez.

Para configurar la dirección una vez durante la sesión de PowerShell:

```powershell
$env:ROBOT_CAMERA_IP = "192.168.43.25"
python camera_test.py
```

Los cuatro programas también aceptan `--url http://IP:81/stream`. La opción de línea de comandos tiene prioridad sobre la variable de entorno. No se requiere editar los scripts ni poner la contraseña WiFi en Python.

## Qué prueba cada programa

| Programa | Resultado |
|---|---|
| `camera_test.py` | Video con la resolución recibida y FPS de recepción/procesamiento. Salir con Q. |
| `deteccion_camino.py` | Reduce VGA/QVGA a 160 × 120 y aplica los umbrales y ROI originales. Distancias en píxeles del cuadro reducido. Salir con Q. |
| `test_fps_latency.py` | Decodifica JPEG, muestra resolución, tamaños y FPS, y resume intervalos. Procesa todos los cuadros completos del búfer. Salir con Q. |
| `test_stream.py` | Cuenta bytes y velocidad de recepción. Salir con Ctrl+C. |

Los FPS de `/status` se miden en el firmware al enviar imágenes; los de Python se miden al recibir/procesar. No tienen por qué coincidir. Ninguna de estas medidas es latencia física entre captura y pantalla. No hay control de motores desde estos programas.

Si no conecta, comprobar IP actual, hotspot común y que no haya otro cliente. Algunos hotspots aíslan sus clientes; si la página tampoco abre desde el PC, revisar esa configuración. Si se reinicia la placa, revisar el registro serie y la alimentación. Confirmar orientación izquierda/derecha con un objeto real antes de usar visión para control.
