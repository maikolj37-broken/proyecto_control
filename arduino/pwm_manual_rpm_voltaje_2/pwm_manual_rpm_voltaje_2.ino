/*
  Control manual de PWM por Serial + medición de RPM filtradas y cálculo de voltaje
  aplicado al motor.

  Uso por Monitor Serial (115200 baudios):
    A<pwm>   -> ej: A180  -> aplica PWM=180 al motor A y lo deja corriendo
    B<pwm>   -> ej: B180  -> aplica PWM=180 al motor B y lo deja corriendo
    A0 / B0  -> detiene ese motor
    S        -> detiene ambos motores
*/

// ---------------- Pines del driver TB6612 ----------------
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

// ---------------- Voltaje de alimentación del TB6612 ----------------
#define V_ALIMENTACION   4.81   // Voltaje real de la fuente dedicada al motor

// ---------------- Calibración de encoder (ticks/vuelta) ----------------
#define CPR_SALIDA_A  78.3
#define CPR_SALIDA_B  69.8
#define ENCA_SIGN  -1
#define ENCB_SIGN   1

// ---------------- PWM (LEDC) ----------------
#define PWM_FREQ        20000
#define PWM_RESOLUTION  8      // 0-255

// ---------------- Impresión de telemetría ----------------
#define SPEED_CALC_INTERVAL_MS  5

// ---------------- Factor de filtrado IIR paso bajo ----------------
// Un valor entre 0.15 y 0.25 elimina la cuantización conservando la dinámica rápida.
#define ALPHA_FILTER 0.20f

volatile long encoderA_count = 0;
volatile long encoderB_count = 0;

int pwmActualA = 0;
int pwmActualB = 0;

long lastEncA_forSpeed = 0;
long lastEncB_forSpeed = 0;
unsigned long lastSpeedCalcTime = 0;

float speedA_rpm = 0;
float speedB_rpm = 0;

// Variables internas para la velocidad cruda sin filtrar
float raw_rpmA = 0;
float raw_rpmB = 0;

void IRAM_ATTR isrEncoderA() {
  if (digitalRead(ENCA_C1) == digitalRead(ENCA_C2)) {
    encoderA_count += ENCA_SIGN;
  } else {
    encoderA_count -= ENCA_SIGN;
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
//               FUNCIÓN: ACCIONAR MOTORES
// ==========================================================
void setMotor(char motor, int speed) {
  speed = constrain(speed, -255, 255);
  int pwmVal = abs(speed);
  digitalWrite(STBY_PIN, HIGH);

  if (motor == 'A') {
    if (speed > 0) { digitalWrite(AIN1_PIN, HIGH); digitalWrite(AIN2_PIN, LOW); }
    else if (speed < 0) { digitalWrite(AIN1_PIN, LOW); digitalWrite(AIN2_PIN, HIGH); }
    else { digitalWrite(AIN1_PIN, LOW); digitalWrite(AIN2_PIN, LOW); }
    ledcWrite(PWMA_PIN, pwmVal);
    pwmActualA = speed;
  } else {
    if (speed > 0) { digitalWrite(BIN1_PIN, HIGH); digitalWrite(BIN2_PIN, LOW); }
    else if (speed < 0) { digitalWrite(BIN1_PIN, LOW); digitalWrite(BIN2_PIN, HIGH); }
    else { digitalWrite(BIN1_PIN, LOW); digitalWrite(BIN2_PIN, LOW); }
    ledcWrite(PWMB_PIN, pwmVal);
    pwmActualB = speed;
  }
}

void stopAllMotors() {
  setMotor('A', 0);
  setMotor('B', 0);
  digitalWrite(STBY_PIN, LOW);
}

// ==========================================================
//     FUNCIÓN: LECTURA Y CÁLCULO DE VELOCIDAD (FILTRADA)
// ==========================================================
bool updateEncoderSpeeds() {
  unsigned long now = millis();
  unsigned long dt_ms = now - lastSpeedCalcTime;
  if (dt_ms < SPEED_CALC_INTERVAL_MS) return false;
  lastSpeedCalcTime = now;

  noInterrupts();
  long a = encoderA_count;
  long b = encoderB_count;
  interrupts();

  long deltaA = a - lastEncA_forSpeed;
  long deltaB = b - lastEncB_forSpeed;
  lastEncA_forSpeed = a;
  lastEncB_forSpeed = b;

  float dt_min = dt_ms / 60000.0;
  
  // 1. Velocidad instantánea (cruda, sensible a la baja resolución de pulsos)
  raw_rpmA = (deltaA / CPR_SALIDA_A) / dt_min;
  raw_rpmB = (deltaB / CPR_SALIDA_B) / dt_min;

  // 2. Filtro exponencial IIR para atenuar la cuantización
  speedA_rpm = (ALPHA_FILTER * raw_rpmA) + ((1.0f - ALPHA_FILTER) * speedA_rpm);
  speedB_rpm = (ALPHA_FILTER * raw_rpmB) + ((1.0f - ALPHA_FILTER) * speedB_rpm);

  return true;
}

// ==========================================================
//     FUNCIÓN: VOLTAJE APLICADO AL MOTOR (calculado, no medido)
// ==========================================================
float calcularVoltajeAplicado(int pwmAplicado) {
  return (abs(pwmAplicado) / 255.0) * V_ALIMENTACION;
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
  lastSpeedCalcTime = millis();

  Serial.println("=== Control manual de PWM + RPM + Voltaje ===");
  Serial.println("Comandos: A<pwm>  B<pwm>  A0  B0  S");
  Serial.println("Ej: A180   (motor A al 180 de PWM, sigue corriendo)");
}

void loop() {
  // Leer comandos por consola
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "S" || cmd == "s") {
      stopAllMotors();
      Serial.println("# Motores detenidos");
    } else if (cmd.length() >= 1 && (cmd[0] == 'A' || cmd[0] == 'a')) {
      int pwmVal = cmd.substring(1).toInt();
      setMotor('A', pwmVal);
      Serial.print("# Motor A -> PWM=");
      Serial.println(pwmVal);
    } else if (cmd.length() >= 1 && (cmd[0] == 'B' || cmd[0] == 'b')) {
      int pwmVal = cmd.substring(1).toInt();
      setMotor('B', pwmVal);
      Serial.print("# Motor B -> PWM=");
      Serial.println(pwmVal);
    }
  }

  // Enviar telemetría si se actualizan las RPM
  if (updateEncoderSpeeds()) {
    if (pwmActualA != 0) {
      float vA = calcularVoltajeAplicado(pwmActualA);
      Serial.print("A,");
      Serial.print(pwmActualA);
      Serial.print(",");
      Serial.print(speedA_rpm, 2);
      Serial.print(",");
      Serial.println(vA, 2);
    }

    if (pwmActualB != 0) {
      float vB = calcularVoltajeAplicado(pwmActualB);
      Serial.print("B,");
      Serial.print(pwmActualB);
      Serial.print(",");
      Serial.print(speedB_rpm, 2);
      Serial.print(",");
      Serial.println(vB, 2);
    }
  }
}