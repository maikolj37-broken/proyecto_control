/*
  Ensayo de respuesta al escalón para identificar la función de
  transferencia de cada motorreductor (modelo de primer orden
  Gp(s) = K / (tau*s + 1)).

  Uso por Monitor Serial (115200 baudios):
    A<pwm>   -> ej: A200  -> aplica escalón de PWM=200 al motor A
    B<pwm>   -> ej: B200  -> aplica escalón de PWM=200 al motor B
    (pwm entre 0 y 255)

  El sketch:
    1. Detiene el motor y espera a que quede en reposo (1 s).
    2. Aplica el escalón de PWM indicado.
    3. Imprime por Serial, en CSV, "t_ms,rpm" cada SAMPLE_MS, durante
       TEST_DURATION_MS.
    4. Detiene el motor al terminar.

  Copia las líneas impresas (desde el encabezado "t_ms,rpm" hasta que
  termina) a un archivo .csv y ajusta el modelo allí (Excel, Python,
  MATLAB, etc.). Repite con al menos 2-3 valores de pwm distintos por
  motor para verificar linealidad.
*/

// ---------------- Pines del driver TB6612 (confirmados) ----------------
#define PWMA_PIN   13
#define AIN1_PIN   33
#define AIN2_PIN   32
#define STBY_PIN   25

#define PWMB_PIN   14
#define BIN1_PIN   26
#define BIN2_PIN   27

// ---------------- Pines de los encoders ----------------
#define ENCA_C1    23
#define ENCA_C2    22
#define ENCB_C1    18
#define ENCB_C2    5

// ---------------- Calibración de encoder (ticks/vuelta medidos) ----------------
#define CPR_SALIDA_A  78.3   // tras el cambio de conectores, ahora en canal A
#define CPR_SALIDA_B  69.8   // tras el cambio de conectores, ahora en canal B

// El motor montado en espejo ahora quedó en el canal B tras el cambio de
// conectores: invierte el signo para que "adelante" sea positivo en ambos.
#define ENCB_SIGN  -1

// ---------------- PWM (LEDC) ----------------
#define PWM_FREQ        20000
#define PWM_RESOLUTION  8

// ---------------- Parámetros del ensayo ----------------
#define TEST_DURATION_MS   3000  // duración del registro tras el escalón
#define SAMPLE_MS          20    // periodo de muestreo para el log
#define REST_BEFORE_MS     1000  // tiempo de reposo antes de aplicar el escalón

volatile long encoderA_count = 0;
volatile long encoderB_count = 0;

void IRAM_ATTR isrEncoderA() {
  if (digitalRead(ENCA_C1) == digitalRead(ENCA_C2)) {
    encoderA_count++;
  } else {
    encoderA_count--;
  }
}

void IRAM_ATTR isrEncoderB() {
  if (digitalRead(ENCB_C1) == digitalRead(ENCB_C2)) {
    encoderB_count += ENCB_SIGN;
  } else {
    encoderB_count -= ENCB_SIGN;
  }
}

// ==========================================================
//              FUNCIÓN: ACCIONAR MOTORES
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

  } else if (motor == 'B') {
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

void stopAllMotors() {
  setMotor('A', 0);
  setMotor('B', 0);
  digitalWrite(STBY_PIN, LOW);
}

// ==========================================================
//     LECTURA DE VELOCIDAD INSTANTÁNEA (RPM) EN UNA VENTANA
// ==========================================================
float readSpeedRPM(char motor, unsigned long window_ms) {
  static long lastA = 0, lastB = 0;

  noInterrupts();
  long a = encoderA_count;
  long b = encoderB_count;
  interrupts();

  float rpm = 0;
  float dt_min = window_ms / 60000.0;

  if (motor == 'A') {
    long delta = a - lastA;
    lastA = a;
    rpm = (delta / CPR_SALIDA_A) / dt_min;
  } else {
    long delta = b - lastB;
    lastB = b;
    rpm = (delta / CPR_SALIDA_B) / dt_min;
  }
  return rpm;
}

// ==========================================================
//                 ENSAYO DE RESPUESTA AL ESCALÓN
// ==========================================================
void runStepTest(char motor, int pwmStep) {
  // Reposo antes del escalón, y reset de la referencia del contador
  stopAllMotors();
  delay(REST_BEFORE_MS);
  readSpeedRPM(motor, 1); // limpia el "lastA/lastB" de referencia

  Serial.println();
  Serial.print("# Ensayo escalon motor ");
  Serial.print(motor);
  Serial.print(" PWM=");
  Serial.println(pwmStep);
  Serial.println("t_ms,rpm");

  unsigned long t0 = millis();
  unsigned long lastSample = t0;

  // Aplica el escalón
  setMotor(motor, pwmStep);

  while (millis() - t0 < TEST_DURATION_MS) {
    if (millis() - lastSample >= SAMPLE_MS) {
      unsigned long dt = millis() - lastSample;
      lastSample = millis();
      float rpm = readSpeedRPM(motor, dt);
      Serial.print(millis() - t0);
      Serial.print(",");
      Serial.println(rpm, 2);
    }
  }

  stopAllMotors();
  Serial.println("# Fin del ensayo");
}

void setup() {
  Serial.begin(115200);

  pinMode(AIN1_PIN, OUTPUT);
  pinMode(AIN2_PIN, OUTPUT);
  pinMode(BIN1_PIN, OUTPUT);
  pinMode(BIN2_PIN, OUTPUT);
  pinMode(STBY_PIN, OUTPUT);

  ledcAttach(PWMA_PIN, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(PWMB_PIN, PWM_FREQ, PWM_RESOLUTION);

  pinMode(ENCA_C1, INPUT_PULLUP);
  pinMode(ENCA_C2, INPUT_PULLUP);
  pinMode(ENCB_C1, INPUT_PULLUP);
  pinMode(ENCB_C2, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENCA_C1), isrEncoderA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCB_C1), isrEncoderB, CHANGE);

  stopAllMotors();

  Serial.println("=== Ensayo de respuesta al escalon ===");
  Serial.println("Comandos: A<pwm>  (ej. A200)   B<pwm>  (ej. B200)");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() >= 2 && (cmd[0] == 'A' || cmd[0] == 'B')) {
      char motor = cmd[0];
      int pwmVal = cmd.substring(1).toInt();
      pwmVal = constrain(pwmVal, 0, 255);
      runStepTest(motor, pwmVal);
    } else if (cmd.length() > 0) {
      Serial.println("Comando invalido. Ejemplo: A200 o B200");
    }
  }
}
