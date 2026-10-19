// ESP32-CAM AI Thinker + OV3660. Arduino-ESP32 3.3.12.
// MJPEG compatible con Robot_OpenCV: http://192.168.4.1:81/stream
#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"

// Clave de demostracion del punto de acceso local, no de una red personal.
static const char *AP_SSID = "RobotCam";
static const char *AP_PASSWORD = "robotcam123";
static const int VFLIP = 0;    // Cambiar a 1 si la imagen queda invertida.
static const int HMIRROR = 0;  // Cambiar a 1 si corresponde al montaje.
static httpd_handle_t webServer = nullptr;
static httpd_handle_t streamServer = nullptr;

static esp_err_t streamHandler(httpd_req_t *req) {
  esp_err_t result = httpd_resp_set_type(req,
      "multipart/x-mixed-replace;boundary=robotcam_frame");
  if (result != ESP_OK) return result;
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  while (true) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) return ESP_FAIL;
    if (frame->format != PIXFORMAT_JPEG) {
      esp_camera_fb_return(frame);
      return ESP_FAIL;
    }
    char header[128];
    int size = snprintf(header, sizeof(header),
        "--robotcam_frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
        static_cast<unsigned>(frame->len));
    result = httpd_resp_send_chunk(req, header, size);
    if (result == ESP_OK)
      result = httpd_resp_send_chunk(req, reinterpret_cast<const char *>(frame->buf), frame->len);
    esp_camera_fb_return(frame);  // Liberar incluso si se desconecta el cliente.
    if (result == ESP_OK) result = httpd_resp_send_chunk(req, "\r\n", 2);
    if (result != ESP_OK) return result;
    delay(1);
  }
}

static esp_err_t indexHandler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_send(req,
      "<!doctype html><html lang='es'><meta charset='utf-8'>"
      "<title>RobotCam</title><h1>RobotCam: prueba OpenCV</h1>"
      "<p>MJPEG 160 x 120. Utiliza un solo cliente de video a la vez.</p>"
      "<p><a href='http://192.168.4.1:81/stream'>Abrir video</a></p>"
      "<p>Cierra el video del navegador antes de ejecutar Python.</p></html>",
      HTTPD_RESP_USE_STRLEN);
}

static void fail(const char *stage, esp_err_t error) {
  Serial.printf("ERROR %s: 0x%x (%s)\n", stage, error, esp_err_to_name(error));
  while (true) delay(1000);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  // Pines de la placa AI Thinker; el sensor no cambia el cableado de la placa.
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 5;  c.pin_d1 = 18; c.pin_d2 = 19; c.pin_d3 = 21;
  c.pin_d4 = 36; c.pin_d5 = 39; c.pin_d6 = 34; c.pin_d7 = 35;
  c.pin_xclk = 0; c.pin_pclk = 22; c.pin_vsync = 25; c.pin_href = 23;
  c.pin_sccb_sda = 26; c.pin_sccb_scl = 27;
  c.pin_pwdn = 32; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QQVGA; // 160 x 120: coincide con deteccion_camino.py.
  c.jpeg_quality = 12;
  const bool psram = psramFound();
  c.fb_count = psram ? 2 : 1;
  c.fb_location = psram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = psram ? CAMERA_GRAB_LATEST : CAMERA_GRAB_WHEN_EMPTY;
  esp_err_t result = esp_camera_init(&c);
  if (result != ESP_OK) fail("inicializando camara (revisar flex, alimentacion y placa)", result);
  sensor_t *sensor = esp_camera_sensor_get();
  if (!sensor) fail("sensor", ESP_FAIL);
  Serial.printf("Sensor PID: 0x%04x | PSRAM: %s\n", sensor->id.PID, psram ? "si" : "no");
  if (sensor->id.PID != OV3660_PID) Serial.println("AVISO: sensor detectado distinto de OV3660.");
  if (sensor->set_vflip(sensor, VFLIP) != 0 || sensor->set_hmirror(sensor, HMIRROR) != 0)
    fail("orientacion del sensor", ESP_FAIL);

  WiFi.mode(WIFI_AP);
  const IPAddress ip(192,168,4,1), mask(255,255,255,0);
  if (!WiFi.softAPConfig(ip, ip, mask) || !WiFi.softAP(AP_SSID, AP_PASSWORD))
    fail("punto de acceso WiFi", ESP_FAIL);
  WiFi.setSleep(false);
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  result = httpd_start(&webServer, &config);
  if (result != ESP_OK) fail("servidor web", result);
  httpd_uri_t index = {};
  index.uri = "/"; index.method = HTTP_GET; index.handler = indexHandler;
  result = httpd_register_uri_handler(webServer, &index);
  if (result != ESP_OK) fail("ruta web", result);

  config.server_port = 81;
  config.ctrl_port += 1; // Cada instancia HTTP necesita su propio puerto de control.
  config.stack_size = 8192;
  config.send_wait_timeout = 5;
  result = httpd_start(&streamServer, &config);
  if (result != ESP_OK) fail("servidor MJPEG", result);
  httpd_uri_t stream = {};
  stream.uri = "/stream"; stream.method = HTTP_GET; stream.handler = streamHandler;
  result = httpd_register_uri_handler(streamServer, &stream);
  if (result != ESP_OK) fail("ruta MJPEG", result);
  Serial.printf("Red: %s | Clave de prueba: %s\n", AP_SSID, AP_PASSWORD);
  Serial.println("Video: http://192.168.4.1:81/stream");
  Serial.println("Ejecutar un solo programa OpenCV a la vez. Sin control de motores.");
}

void loop() { delay(1000); }
