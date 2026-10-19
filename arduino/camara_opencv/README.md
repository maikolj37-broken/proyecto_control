# Cargar y probar ESP32-CAM AI Thinker + OV3660

## 1. Cargar el firmware

1. Abrir `camara_opencv.ino` de la carpeta `arduino/camara_opencv` (o la nueva carpeta en tus códigos originales de Arduino).
2. En Arduino IDE seleccionar paquete **esp32 by Espressif Systems 3.3.12**, placa **AI Thinker ESP32-CAM** y el puerto del adaptador. La PSRAM debe estar habilitada según la configuración de esa placa.
3. Si se usa adaptador USB-UART: alimentación estable de 5 V al pin 5V y GND común; señales UART de 3.3 V, TX del adaptador a U0R y RX a U0T. No aplicar 5 V a las señales UART. Conectar GPIO0 a GND y reiniciar para cargar. Con una base ESP32-CAM-MB, seguir el procedimiento de carga de la base.
4. Subir el sketch. Retirar GPIO0 de GND y reiniciar para ejecución normal. Abrir monitor serie a **115200**.
5. Confirmar que no aparece error de cámara, que se informa el PID del sensor y que aparece la dirección del video. El firmware mantiene el detector de brownout activo; si se reinicia, revisar alimentación y cableado.

## 2. Conectar el computador

Instalar las dependencias antes de cambiar de WiFi (la red de cámara no proporciona Internet):

```powershell
cd C:\Users\Usuario\Desktop\Robot_OpenCV
python -m pip install -r requirements.txt
```

Conectar el PC a **RobotCam**, clave **robotcam123**. Mantener la conexión aunque Windows indique que no hay Internet. Abrir `http://192.168.4.1/` y, si se desea, el enlace al video. Cerrar ese video antes de iniciar Python: el servidor está diseñado para un cliente de streaming a la vez.

## 3. Probar los programas existentes

Ejecutar uno a la vez desde `Robot_OpenCV`:

| Comando | Qué comprobar | Salir |
|---|---|---|
| `python test_stream.py` | Aumentan los bytes recibidos. No comprueba la detección de línea. | Ctrl+C |
| `python camera_test.py` | Imagen visible de 160 × 120 y FPS. | Q con ventana enfocada |
| `python test_fps_latency.py` | Recepción y decodificación de JPEG. Sus intervalos pueden verse afectados por el búfer y no representan latencia de captura. | Q |
| `python deteccion_camino.py` | Detección de línea oscura, región de interés y centros en la imagen. Ajustar iluminación y altura antes de cambiar umbrales. | Q |

La URL ya coincide en los cuatro scripts; no hay que editarla. Si la imagen queda invertida o reflejada, cambiar `VFLIP` o `HMIRROR` en el sketch y volver a cargar. Confirmar izquierda/derecha con un objeto real antes de usar el error de visión en control.

## 4. Límites y diagnóstico

- `MotorTest` de los sketches de motores también utiliza 192.168.4.1, pero es otra red. Para esta prueba conectarse a `RobotCam`. La conexión simultánea y el envío de comandos a motores requerirán otra etapa de integración.
- Si no abre el video, comprobar la red seleccionada, el monitor serie y que ningún otro programa/navegador mantiene abierto `/stream`.
- Si falla `esp_camera_init`, comprobar placa AI Thinker, flex del sensor con la placa apagada y alimentación. El firmware imprime el código de error y se detiene.
- Si se corta, revisar primero alimentación, cobertura y clientes duplicados. No se promete una tasa de FPS antes de medir en el equipo real.
- Esta guía no implica que la carga o la prueba física ya se hayan realizado.
