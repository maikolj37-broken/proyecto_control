
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ================================
// WIFI DEL CELULAR
// ================================
#include "secrets.h"
const char* ssid = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ================================
// PINES ESP32-CAM AI THINKER
// ================================
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5

#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

WebServer server(80);
WiFiServer streamServer(81);

// ================================
// MEDICION DE FPS
// ================================
volatile float fpsActual = 0;
volatile unsigned long totalFrames = 0;

// ================================
// PAGINA WEB
// ================================
void handleRoot() {

  String html = R"rawliteral(
<!DOCTYPE html>
<html lang="es">
<head>
<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>ESP32-CAM STREAM</title>

<style>
body {
  background: #101218;
  color: white;
  text-align: center;
  font-family: Arial;
  margin: 20px;
}

.video {
  position: relative;
  display: inline-block;
  width: 100%;
  max-width: 850px;
}

img {
  width: 100%;
  border-radius: 12px;
}

.fps {
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(0,0,0,0.75);
  color: #00ff88;
  padding: 10px;
  border-radius: 7px;
  font-size: 20px;
  font-weight: bold;
}

.info {
  margin-top: 15px;
  color: #aaa;
}
</style>
</head>

<body>

<h2>ESP32-CAM | STREAM EN VIVO</h2>

<div class="video">
  <img id="stream">
  <div class="fps" id="fps">
    FPS: 0.0
  </div>
</div>

<div class="info" id="info">
  Conectando...
</div>

<script>

const host = window.location.hostname;

document.getElementById("stream").src =
  "http://" + host + ":81/stream";

async function actualizarFPS() {
  try {
    const response = await fetch("/status");
    const data = await response.json();

    document.getElementById("fps").innerText =
      "FPS: " + data.fps.toFixed(1);

    document.getElementById("info").innerText =
      "Frames: " + data.frames +
      " | Resolucion: " + data.resolution;

  } catch(e) {
    document.getElementById("info").innerText =
      "Sin datos del servidor";
  }
}

setInterval(actualizarFPS, 1000);
actualizarFPS();

</script>
</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

// ================================
// ESTADO DEL STREAM
// ================================
void handleStatus() {

  String json = "{";
  json += "\"fps\":" + String(fpsActual, 2);
  json += ",\"frames\":" + String(totalFrames);
  json += ",\"resolution\":\"";

  json += psramFound() ? "VGA" : "QVGA";

  json += "\"}";

  server.send(200, "application/json", json);
}

// ================================
// STREAM MJPEG
// ================================
void handleStream() {

  WiFiClient client = streamServer.available();

  if (!client) return;

  client.setTimeout(1000);

  unsigned long inicio = millis();

  while (client.connected() && !client.available()) {
    if (millis() - inicio > 2000) {
      client.stop();
      return;
    }
    delay(1);
  }

  while (client.available()) {
    String line = client.readStringUntil('\n');
    if (line == "\r") break;
  }

  client.print(
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: multipart/x-mixed-replace;"
    "boundary=frame\r\n"
    "Cache-Control: no-cache\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\n"
  );

  unsigned long tiempoFPS = millis();
  unsigned long ultimoFrame = millis();
  unsigned long framesIntervalo = 0;

  while (client.connected()) {

    camera_fb_t* fb = esp_camera_fb_get();

    if (!fb) {
      Serial.println("Error capturando imagen");
      break;
    }

    size_t longitud = fb->len;

    client.printf(
      "--frame\r\n"
      "Content-Type: image/jpeg\r\n"
      "Content-Length: %u\r\n\r\n",
      (unsigned int)longitud
    );

    size_t enviados =
      client.write(fb->buf, longitud);

    client.print("\r\n");

    esp_camera_fb_return(fb);

    if (enviados != longitud) break;

    totalFrames++;
    framesIntervalo++;

    unsigned long ahora = millis();

    // FPS instantaneo suavizado
    unsigned long delta = ahora - ultimoFrame;

    if (delta > 0) {
      float fpsInstantaneo = 1000.0f / delta;

      fpsActual =
        0.8f * fpsActual +
        0.2f * fpsInstantaneo;
    }

    ultimoFrame = ahora;

    // Reporte cada segundo
    if (ahora - tiempoFPS >= 1000) {

      float fpsMedido =
        framesIntervalo * 1000.0f /
        (ahora - tiempoFPS);

      fpsActual = fpsMedido;

      Serial.printf(
        "FPS: %.2f | Frames: %lu\n",
        fpsActual,
        totalFrames
      );

      framesIntervalo = 0;
      tiempoFPS = ahora;
    }

    // Permite atender /status
    server.handleClient();

    delay(1);
  }

  fpsActual = 0;
  client.stop();
}

// ================================
// SETUP
// ================================
void setup() {

  Serial.begin(115200);
  delay(1000);

  camera_config_t config = {};

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {

    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;

  } else {

    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf(
      "Error camara: 0x%x\n", err
    );
    return;
  }

  // ================================
  // ROTACION DE 180 GRADOS
  // ================================
  sensor_t* sensor = esp_camera_sensor_get();

  if (sensor != NULL) {
    sensor->set_vflip(sensor, 1);
    sensor->set_hmirror(sensor, 1);
  }

  Serial.println("Camara rotada 180 grados");

  // ================================
  // WIFI MODO STA
  // ================================
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  WiFi.begin(ssid, password);

  Serial.print("Conectando a WiFi");

  unsigned long inicioWiFi = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - inicioWiFi < 20000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nError conectando a WiFi");
    return;
  }

  Serial.println("\nWiFi conectado");

  Serial.print("Direccion IP: ");
  Serial.println(WiFi.localIP());

  Serial.print("RSSI: ");
  Serial.println(WiFi.RSSI());

  // ================================
  // SERVIDORES
  // ================================
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);

  server.begin();
  streamServer.begin();

  Serial.println("Servidor iniciado");

  Serial.print("Abrir en navegador: http://");
  Serial.println(WiFi.localIP());
}

// ================================
// LOOP
// ================================
void loop() {
  server.handleClient();
  handleStream();
  delay(1);
}
