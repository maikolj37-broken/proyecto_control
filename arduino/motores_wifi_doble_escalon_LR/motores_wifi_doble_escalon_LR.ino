#include <WiFi.h>
#include <WebServer.h>

// ==========================================================
//                     WIFI ACCESS POINT
// ==========================================================

const char* WIFI_SSID     = "MotorTest";
const char* WIFI_PASSWORD = "motores123";

WebServer server(80);

// ==========================================================
//                     PINES TB6612
// ==========================================================

// MOTOR A = IZQUIERDO
#define PWMA_PIN   14
#define AIN1_PIN   26
#define AIN2_PIN   27
#define STBY_PIN   25

// MOTOR B = DERECHO
#define PWMB_PIN   13
#define BIN1_PIN   33
#define BIN2_PIN   32

// ==========================================================
//                     ENCODERS
// ==========================================================

// A (izquierdo)
#define ENCA_C1    18
#define ENCA_C2    5

// B (derecho)
#define ENCB_C1    23
#define ENCB_C2    22

// ==========================================================
//                     ALIMENTACION
// ==========================================================

#define V_ALIMENTACION   4.81

// ==========================================================
//                  CALIBRACION ENCODERS
// ==========================================================

#define CPR_SALIDA_A  69.8
#define CPR_SALIDA_B  78.3

#define ENCA_SIGN   1
#define ENCB_SIGN  -1

// ==========================================================
//              GANANCIA ESTATICA RPM/V
// ==========================================================

#define K_RPM_POR_V_A  516.1
#define K_RPM_POR_V_B  413.1

// ==========================================================
//                         PWM
// ==========================================================

#define PWM_FREQ        20000
#define PWM_RESOLUTION  8

// ==========================================================
//                  ENSAYO DOBLE ESCALON
// ==========================================================

#define BASELINE_PWM     230
#define STEP_PERCENT     10.0

#define T_BASE_MS        2000
#define T_POST_MS        3500

// ==========================================================
//                  MUESTREO
// ==========================================================

// 1 ms = 1000 Hz
#define SAMPLE_MS        1

// Si pasan 300 ms sin nuevo pulso -> RPM = 0
#define STALE_US         300000UL

// 3 segundos / 1 ms = 3000 muestras
#define MAX_SAMPLES      3050

// ==========================================================
//                  DATOS DE ENCODER
// ==========================================================

volatile unsigned long lastEdgeUsA = 0;
volatile unsigned long lastPeriodUsA = 0;
volatile int lastDirA = 0;

volatile unsigned long lastEdgeUsB = 0;
volatile unsigned long lastPeriodUsB = 0;
volatile int lastDirB = 0;

// ==========================================================
//                     BUFFER DE DATOS
// ==========================================================
//
// IMPORTANTE:
// Solo guardamos tiempo + RPM bruto.
// Los filtros 3, 5 y 7 se calculan al descargar el CSV.
// Esto ahorra mucha RAM.
//
// ==========================================================

struct Sample {
  unsigned long t_us;
  float rpm_bruto;
};

Sample bufferA[MAX_SAMPLES];
Sample bufferB[MAX_SAMPLES];

int countA = 0;
int countB = 0;

// ==========================================================
//                  INTERRUPCIONES ENCODER
// ==========================================================

void IRAM_ATTR isrEncoderA() {

  unsigned long now = micros();

  lastPeriodUsA = now - lastEdgeUsA;
  lastEdgeUsA = now;

  bool forward =
    (digitalRead(ENCA_C1) == digitalRead(ENCA_C2));

  lastDirA = forward ? ENCA_SIGN : -ENCA_SIGN;
}

void IRAM_ATTR isrEncoderB() {

  unsigned long now = micros();

  lastPeriodUsB = now - lastEdgeUsB;
  lastEdgeUsB = now;

  bool forward =
    (digitalRead(ENCB_C1) == digitalRead(ENCB_C2));

  lastDirB = forward ? ENCB_SIGN : -ENCB_SIGN;
}

// ==========================================================
//                RPM INSTANTANEA
// ==========================================================

float calcularRPMInstantanea(char motor) {

  unsigned long periodUs;
  unsigned long lastEdge;
  int dir;

  noInterrupts();

  if (motor == 'A') {

    periodUs = lastPeriodUsA;
    lastEdge = lastEdgeUsA;
    dir = lastDirA;

  } else {

    periodUs = lastPeriodUsB;
    lastEdge = lastEdgeUsB;
    dir = lastDirB;
  }

  interrupts();

  if (periodUs == 0)
    return 0;

  unsigned long sinceEdge = micros() - lastEdge;

  if (sinceEdge > STALE_US)
    return 0;

  unsigned long effPeriod =
    (sinceEdge > periodUs) ? sinceEdge : periodUs;

  float cpr =
    (motor == 'A') ? CPR_SALIDA_A : CPR_SALIDA_B;

  float rpm =
    60000000.0f /
    (cpr * (float)effPeriod);

  return dir * rpm;
}

// ==========================================================
//                     CONTROL MOTOR
// ==========================================================

void setMotor(char motor, int speed) {

  speed = constrain(speed, -255, 255);

  int pwmVal = abs(speed);

  digitalWrite(STBY_PIN, HIGH);

  if (motor == 'A') {

    if (speed > 0) {

      digitalWrite(AIN1_PIN, HIGH);
      digitalWrite(AIN2_PIN, LOW);

    } else if (speed < 0) {

      digitalWrite(AIN1_PIN, LOW);
      digitalWrite(AIN2_PIN, HIGH);

    } else {

      digitalWrite(AIN1_PIN, LOW);
      digitalWrite(AIN2_PIN, LOW);
    }

    ledcWrite(PWMA_PIN, pwmVal);

  } else {

    if (speed > 0) {

      digitalWrite(BIN1_PIN, HIGH);
      digitalWrite(BIN2_PIN, LOW);

    } else if (speed < 0) {

      digitalWrite(BIN1_PIN, LOW);
      digitalWrite(BIN2_PIN, HIGH);

    } else {

      digitalWrite(BIN1_PIN, LOW);
      digitalWrite(BIN2_PIN, LOW);
    }

    ledcWrite(PWMB_PIN, pwmVal);
  }
}

// ==========================================================
//                     DETENER MOTORES
// ==========================================================

void stopAllMotors() {

  setMotor('A', 0);
  setMotor('B', 0);
}

// ==========================================================
//                VOLTAJE SEGUN PWM
// ==========================================================

float calcularVoltajeAplicado(int pwmAplicado) {

  return
    (abs(pwmAplicado) / 255.0f) *
    V_ALIMENTACION;
}

// ==========================================================
//          MEDIA MOVIL DE N MUESTRAS
// ==========================================================
//
// Calcula retrospectivamente la media móvil.
// No modifica el buffer.
// ==========================================================

float calcularMediaMovil(
  Sample *buf,
  int index,
  int total,
  int ventana
) {

  float suma = 0.0;

  int inicio = index - ventana + 1;

  if (inicio < 0)
    inicio = 0;

  int cantidad = 0;

  for (int i = inicio; i <= index; i++) {

    suma += buf[i].rpm_bruto;
    cantidad++;
  }

  if (cantidad == 0)
    return 0;

  return suma / cantidad;
}

// ==========================================================
//                 ENSAYO DOBLE ESCALON
// ==========================================================

int runDoubleStepTest(char motor) {

  char otro =
    (motor == 'A') ? 'B' : 'A';

  Sample *buf =
    (motor == 'A') ? bufferA : bufferB;

  setMotor(otro, 0);
  setMotor(motor, 0);

  delay(300);

  int basePwm = BASELINE_PWM;

  int stepPwm =
    (int)round(
      basePwm *
      (1.0 + STEP_PERCENT / 100.0)
    );

  stepPwm =
    constrain(stepPwm, 0, 255);

  int n = 0;

  unsigned long tStart = micros();

  unsigned long tStep =
    tStart +
    (unsigned long)T_BASE_MS * 1000UL;

  unsigned long tEnd =
    tStep +
    (unsigned long)T_POST_MS * 1000UL;

  unsigned long nextSampleUs =
    tStart;

  setMotor(motor, basePwm);

  bool stepped = false;

  while (true) {

    unsigned long now = micros();

    if (now >= tEnd)
      break;

    // ------------------------------------------------------
    // ESCALON BASELINE -> BASELINE + STEP_PERCENT
    // ------------------------------------------------------

    if (!stepped && now >= tStep) {

      setMotor(motor, stepPwm);

      stepped = true;
    }

    // ------------------------------------------------------
    // MUESTREO CADA 1 ms
    // ------------------------------------------------------

    if (now >= nextSampleUs) {

      nextSampleUs +=
        (unsigned long)SAMPLE_MS * 1000UL;

      if (n < MAX_SAMPLES) {

        float rpm =
          calcularRPMInstantanea(motor);

        buf[n].t_us =
          now - tStart;

        buf[n].rpm_bruto =
          rpm;

        n++;
      }
    }
  }

  setMotor(motor, 0);

  if (motor == 'A')
    countA = n;
  else
    countB = n;

  return n;
}

// ==========================================================
//                     PAGINA WEB
// ==========================================================

const char PAGINA_PRINCIPAL[] PROGMEM = R"HTML(

<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>Ensayo de motores</title>

<style>

body{
font-family:sans-serif;
text-align:center;
margin-top:50px
}

button,a.btn{
font-size:20px;
padding:16px 30px;
margin:10px;
border-radius:10px;
border:none;
color:white;
text-decoration:none;
display:inline-block;
cursor:pointer
}

.run-a{
background:#2563eb
}

.run-b{
background:#dc2626
}

.dl-a{
background:#1e3a8a
}

.dl-b{
background:#7f1d1d
}

</style>

</head>

<body>

<h2>Ensayo de doble escalon</h2>

<p>
Muestreo objetivo: 1 ms (1000 Hz)
</p>

<p>
PWM: 230 → 253 (+10%)
</p>

<p>
Filtros: media movil 3, 5 y 7 muestras
</p>

<button
class="run-a"
onclick="location.href='/startA'">
Correr Motor A (izquierdo)
</button>

<button
class="run-b"
onclick="location.href='/startB'">
Correr Motor B (derecho)
</button>

<br>

<a
class="btn dl-a"
href="/motorA.csv">
Descargar CSV A (izq.)
</a>

<a
class="btn dl-b"
href="/motorB.csv">
Descargar CSV B (der.)
</a>

</body>

</html>

)HTML";

// ==========================================================
//                     ROOT
// ==========================================================

void handleRoot() {

  server.send(
    200,
    "text/html",
    PAGINA_PRINCIPAL
  );
}

// ==========================================================
//                     START
// ==========================================================

void handleStart(char motor) {

  int n =
    runDoubleStepTest(motor);

  String msg =
    "<html><body "
    "style='font-family:sans-serif;"
    "text-align:center;margin-top:50px'>";

  msg +=
    "<h3>Ensayo motor " +
    String(motor) +
    " completo</h3>";

  msg +=
    "<p>Muestras capturadas: " +
    String(n) +
    "</p>";

  msg +=
    "<p><a href='/motor" +
    String(motor) +
    ".csv'>"
    "Descargar CSV " +
    String(motor) +
    "</a></p>";

  msg +=
    "<p><a href='/'>Volver</a></p>";

  msg += "</body></html>";

  server.send(
    200,
    "text/html",
    msg
  );
}

void handleStartA() {
  handleStart('A');
}

void handleStartB() {
  handleStart('B');
}

// ==========================================================
//                    DESCARGAR CSV
// ==========================================================

void handleDownload(char motor) {

  Sample *buf =
    (motor == 'A') ? bufferA : bufferB;

  int n =
    (motor == 'A') ? countA : countB;

  float kMotor =
    (motor == 'A')
      ? K_RPM_POR_V_A
      : K_RPM_POR_V_B;

  String filename =
    String("motor") +
    motor +
    ".csv";

  server.sendHeader(
    "Content-Disposition",
    "attachment; filename=" + filename
  );

  server.setContentLength(
    CONTENT_LENGTH_UNKNOWN
  );

  server.send(
    200,
    "text/csv",
    ""
  );

  // --------------------------------------------------------
  // ENCABEZADO
  // --------------------------------------------------------

  server.sendContent(
    "t_s,pwm,"
    "rpm_bruto,"
    "rpm_filtro_3,"
    "rpm_filtro_5,"
    "rpm_filtro_7,"
    "voltaje_pwm,"
    "voltaje_equiv_bruto,"
    "voltaje_equiv_filtro_3,"
    "voltaje_equiv_filtro_5,"
    "voltaje_equiv_filtro_7,"
    "Ts_ms\n"
  );

  // --------------------------------------------------------
  // DATOS
  // --------------------------------------------------------

  char line[300];

  for (int i = 0; i < n; i++) {

    float rpmBruto =
      buf[i].rpm_bruto;

    float rpm3 =
      calcularMediaMovil(
        buf,
        i,
        n,
        3
      );

    float rpm5 =
      calcularMediaMovil(
        buf,
        i,
        n,
        5
      );

    float rpm7 =
      calcularMediaMovil(
        buf,
        i,
        n,
        7
      );

    // ------------------------------------------------------
    // PWM SEGUN EL TIEMPO
    // ------------------------------------------------------

    unsigned long tUs =
      buf[i].t_us;

    int pwmActual;

    if (tUs <
        (unsigned long)T_BASE_MS * 1000UL) {

      pwmActual =
        BASELINE_PWM;

    } else {

      pwmActual =
        (int)round(
          BASELINE_PWM *
          (1.0 +
           STEP_PERCENT / 100.0)
        );
    }

    // ------------------------------------------------------
    // VOLTAJE PWM
    // ------------------------------------------------------

    float voltajePWM =
      calcularVoltajeAplicado(
        pwmActual
      );

    // ------------------------------------------------------
    // VOLTAJES EQUIVALENTES
    // ------------------------------------------------------

    float voltajeEquivBruto =
      rpmBruto / kMotor;

    float voltajeEquiv3 =
      rpm3 / kMotor;

    float voltajeEquiv5 =
      rpm5 / kMotor;

    float voltajeEquiv7 =
      rpm7 / kMotor;

    // ------------------------------------------------------
    // Ts REAL
    // ------------------------------------------------------

    float Ts_ms = 0.0;

    if (i > 0) {

      Ts_ms =
        (buf[i].t_us -
         buf[i - 1].t_us)
        / 1000.0f;
    }

    // ------------------------------------------------------
    // LINEA CSV
    // ------------------------------------------------------

    snprintf(
      line,
      sizeof(line),

      "%.6f,%d,"
      "%.3f,%.3f,%.3f,%.3f,"
      "%.3f,"
      "%.3f,%.3f,%.3f,%.3f,"
      "%.3f\n",

      buf[i].t_us / 1000000.0,

      pwmActual,

      rpmBruto,
      rpm3,
      rpm5,
      rpm7,

      voltajePWM,

      voltajeEquivBruto,
      voltajeEquiv3,
      voltajeEquiv5,
      voltajeEquiv7,

      Ts_ms
    );

    server.sendContent(line);
  }

  server.sendContent("");
}

// ==========================================================
//                  DOWNLOAD A / B
// ==========================================================

void handleDownloadA() {
  handleDownload('A');
}

void handleDownloadB() {
  handleDownload('B');
}

// ==========================================================
//                         SETUP
// ==========================================================

void setup() {

  Serial.begin(115200);

  // --------------------------------------------------------
  // PINES TB6612
  // --------------------------------------------------------

  pinMode(AIN1_PIN, OUTPUT);
  pinMode(AIN2_PIN, OUTPUT);

  pinMode(BIN1_PIN, OUTPUT);
  pinMode(BIN2_PIN, OUTPUT);

  pinMode(STBY_PIN, OUTPUT);

  // --------------------------------------------------------
  // PWM
  // --------------------------------------------------------

  ledcAttach(
    PWMA_PIN,
    PWM_FREQ,
    PWM_RESOLUTION
  );

  ledcAttach(
    PWMB_PIN,
    PWM_FREQ,
    PWM_RESOLUTION
  );

  // --------------------------------------------------------
  // ENCODERS
  // --------------------------------------------------------

  pinMode(
    ENCA_C1,
    INPUT_PULLUP
  );

  pinMode(
    ENCA_C2,
    INPUT_PULLUP
  );

  pinMode(
    ENCB_C1,
    INPUT_PULLUP
  );

  pinMode(
    ENCB_C2,
    INPUT_PULLUP
  );

  attachInterrupt(
    digitalPinToInterrupt(ENCA_C1),
    isrEncoderA,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(ENCB_C1),
    isrEncoderB,
    CHANGE
  );

  // --------------------------------------------------------
  // MOTORES
  // --------------------------------------------------------

  stopAllMotors();

  digitalWrite(
    STBY_PIN,
    LOW
  );

  // --------------------------------------------------------
  // WIFI
  // --------------------------------------------------------

  WiFi.softAP(
    WIFI_SSID,
    WIFI_PASSWORD
  );

  Serial.print(
    "# AP creado. Conectate a la red \""
  );

  Serial.print(WIFI_SSID);

  Serial.println(
    "\" y entra a http://192.168.4.1/"
  );

  // --------------------------------------------------------
  // SERVIDOR
  // --------------------------------------------------------

  server.on(
    "/",
    handleRoot
  );

  server.on(
    "/startA",
    handleStartA
  );

  server.on(
    "/startB",
    handleStartB
  );

  server.on(
    "/motorA.csv",
    handleDownloadA
  );

  server.on(
    "/motorB.csv",
    handleDownloadB
  );

  server.begin();

  Serial.println("# Listo.");

  Serial.println(
    "# Ts objetivo: 1 ms"
  );

  Serial.println(
    "# Frecuencia objetivo: 1000 Hz"
  );

  Serial.println(
    "# Filtros: SMA 3, SMA 5, SMA 7"
  );
}

// ==========================================================
//                          LOOP
// ==========================================================

void loop() {

  server.handleClient();
}