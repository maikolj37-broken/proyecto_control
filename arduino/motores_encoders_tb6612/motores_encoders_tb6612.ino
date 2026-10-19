/*
  Prueba de motores + encoders
  - ESP32 estándar
  - 2x motorreductor CC JGA12-N20B (12 mm) con encoder
  - Driver puente H TB6612FNG

  Motor A = IZQUIERDA
  Motor B = DERECHA

  NOTA DE PINOUT (ya corregido):
  Originalmente PWMA y BIN2 compartían el pin D27 por un error de PCB.
  Se cortó la pista que los unía. Cableado final confirmado:
  PWMA=D13, BIN2=D27 (funcionando, motores independientes).

  Encoders:
  Motor A: C1=D23, C2=D22
  Motor B: C1=D18, C2=D5
*/

// ---------------- Pines del driver TB6612 ----------------
#define PWMA_PIN   13   // PWM motor A (confirmado tras corregir el cableado)
#define AIN1_PIN   33
#define AIN2_PIN   32
#define STBY_PIN   25

#define PWMB_PIN   14   // PWM motor B
#define BIN1_PIN   26
#define BIN2_PIN   27   // confirmado tras corregir el cableado

// ---------------- Pines de los encoders ----------------
#define ENCA_C1    23   // Encoder motor A, canal 1
#define ENCA_C2    22   // Encoder motor A, canal 2

#define ENCB_C1    18   // Encoder motor B, canal 1
#define ENCB_C2    5    // Encoder motor B, canal 2

// ---------------- Parámetros del encoder / reductor ----------------
// Estos dos valores se miden con el sketch calibracion_encoder.ino:
// gira el eje de salida un número exacto de vueltas a mano y compara
// contra el conteo de pulsos. Reemplaza estos números por los que
// obtengas ahí (pueden ser distintos entre motor A y B por tolerancias
// de fabricación del gearbox/encoder).
#define CPR_SALIDA_A  69.8   // ticks/vuelta medidos para el motor A (calibrado con 10 vueltas: -698 ticks)
#define CPR_SALIDA_B  78.3   // ticks/vuelta medidos para el motor B (calibrado con 10 vueltas: 783 ticks)

// ---------------- PWM (LEDC) ----------------
#define PWM_FREQ        20000   // 20 kHz, fuera del rango audible
#define PWM_RESOLUTION  8       // 8 bits -> 0-255

// ---------------- Variables de encoders (volatile: se tocan en ISR) ----------------
volatile long encoderA_count = 0;
volatile long encoderB_count = 0;

long lastEncoderA_count = 0;
long lastEncoderB_count = 0;

float speedA_rpm = 0;
float speedB_rpm = 0;

unsigned long lastSpeedCalcTime = 0;
const unsigned long SPEED_CALC_INTERVAL_MS = 100; // calcular velocidad cada 100 ms

// ==========================================================
//                 INTERRUPCIONES DE ENCODER
// ==========================================================
// Decodificación en cuadratura simple: interrumpe en cualquier cambio
// de C1, y usa el estado de C2 para saber el sentido de giro.

// El motor A está montado en espejo respecto al B (izquierda/derecha), así
// que al avanzar ambos giran físicamente en sentidos opuestos y sus
// encoders cuentan con signo contrario. Invertimos aquí el de A para que
// "adelante" sea positivo en los dos y "atrás" negativo en los dos.
#define ENCA_SIGN  -1

void IRAM_ATTR isrEncoderA() {
  if (digitalRead(ENCA_C1) == digitalRead(ENCA_C2)) {
    encoderA_count += ENCA_SIGN;
  } else {
    encoderA_count -= ENCA_SIGN;
  }
}

void IRAM_ATTR isrEncoderB() {
  if (digitalRead(ENCB_C1) == digitalRead(ENCB_C2)) {
    encoderB_count++;
  } else {
    encoderB_count--;
  }
}

// ==========================================================
//              FUNCIÓN: ACCIONAR MOTORES
// ==========================================================
// motor: 'A' o 'B'
// speed: -255 a 255 (signo = sentido de giro, 0 = detenido)
void setMotor(char motor, int speed) {
  speed = constrain(speed, -255, 255);
  int pwmVal = abs(speed);

  digitalWrite(STBY_PIN, HIGH); // sacar el driver de standby

  if (motor == 'A') {
    if (speed > 0) {
      digitalWrite(AIN1_PIN, HIGH);
      digitalWrite(AIN2_PIN, LOW);
    } else if (speed < 0) {
      digitalWrite(AIN1_PIN, LOW);
      digitalWrite(AIN2_PIN, HIGH);
    } else {
      // frenado activo (short brake)
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

// Detiene ambos motores y activa standby del driver
void stopAllMotors() {
  setMotor('A', 0);
  setMotor('B', 0);
  digitalWrite(STBY_PIN, LOW);
}

// ==========================================================
//     FUNCIÓN: LECTURA Y CÁLCULO DE VELOCIDAD (RPM)
// ==========================================================
// Debe llamarse periódicamente desde loop(); internamente respeta
// el intervalo SPEED_CALC_INTERVAL_MS para no recalcular en cada ciclo.
void updateEncoderSpeeds() {
  unsigned long now = millis();
  if (now - lastSpeedCalcTime < SPEED_CALC_INTERVAL_MS) return;

  unsigned long dt_ms = now - lastSpeedCalcTime;
  lastSpeedCalcTime = now;

  // Copiar contadores volátiles de forma segura
  noInterrupts();
  long countA = encoderA_count;
  long countB = encoderB_count;
  interrupts();

  long deltaA = countA - lastEncoderA_count;
  long deltaB = countB - lastEncoderB_count;

  lastEncoderA_count = countA;
  lastEncoderB_count = countB;

  float dt_min = dt_ms / 60000.0; // ms -> minutos

  // RPM = (pulsos en el intervalo / pulsos por vuelta del eje de salida) / tiempo en minutos
  speedA_rpm = (deltaA / CPR_SALIDA_A) / dt_min;
  speedB_rpm = (deltaB / CPR_SALIDA_B) / dt_min;
}

// ==========================================================
//                        SETUP
// ==========================================================
void setup() {
  Serial.begin(115200);

  // Pines de control del driver
  pinMode(AIN1_PIN, OUTPUT);
  pinMode(AIN2_PIN, OUTPUT);
  pinMode(BIN1_PIN, OUTPUT);
  pinMode(BIN2_PIN, OUTPUT);
  pinMode(STBY_PIN, OUTPUT);

  // PWM con LEDC (API por pin, ESP32 Arduino core 3.x)
  ledcAttach(PWMA_PIN, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(PWMB_PIN, PWM_FREQ, PWM_RESOLUTION);

  // Pines de encoders
  pinMode(ENCA_C1, INPUT_PULLUP);
  pinMode(ENCA_C2, INPUT_PULLUP);
  pinMode(ENCB_C1, INPUT_PULLUP);
  pinMode(ENCB_C2, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENCA_C1), isrEncoderA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCB_C1), isrEncoderB, CHANGE);

  stopAllMotors();

  lastSpeedCalcTime = millis();

  Serial.println("Listo. Iniciando secuencia de prueba...");
}

// ==========================================================
//                         LOOP
// ==========================================================
void loop() {
  // --- Secuencia de prueba simple ---
  // Adelante ambos motores
  setMotor('A', 150);
  setMotor('B', 150);
  testDurante(2000);

  // Detener
  setMotor('A', 0);
  setMotor('B', 0);
  testDurante(500);

  // Reversa ambos motores
  setMotor('A', -150);
  setMotor('B', -150);
  testDurante(2000);

  // Detener
  setMotor('A', 0);
  setMotor('B', 0);
  testDurante(1000);
}

// Corre el loop de velocidad/telemetría durante 'ms' milisegundos
// sin bloquear la actualización de velocidad
void testDurante(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    updateEncoderSpeeds();

    static unsigned long lastPrint = 0;
    if (millis() - lastPrint >= 200) {
      lastPrint = millis();
      Serial.print("Motor A: ");
      Serial.print(speedA_rpm, 1);
      Serial.print(" RPM | Motor B: ");
      Serial.print(speedB_rpm, 1);
      Serial.println(" RPM");
    }
  }
}
