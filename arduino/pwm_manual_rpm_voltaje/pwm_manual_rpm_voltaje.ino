
/*
  Control manual de PWM por Serial + medicion de RPM y voltaje del motor.

  Uso por Monitor Serial (115200 baudios):
    A<pwm>   -> ej: A180  -> aplica PWM=180 al motor A y lo deja corriendo
    B<pwm>   -> ej: B180  -> aplica PWM=180 al motor B y lo deja corriendo
    A0 / B0  -> detiene ese motor
    S        -> detiene ambos motores

  Mientras un motor está corriendo, se imprime cada PRINT_MS:
    motor,pwm,rpm,voltaje

  Adicionalmente:
    Cada vez que se cambia el PWM, se muestra el promedio de RPM
    obtenido durante el PWM anterior.

  *** IMPORTANTE: medicion de voltaje ***
  El ESP32 NO puede leer directamente el voltaje del motor (puede ser
  de varios V hasta >20V); su ADC solo admite hasta ~3.3V. Necesitas
  un DIVISOR RESISTIVO entre la terminal del motor y el pin ADC:

      Motor(+) ---[ R1 ]---+---[ R2 ]--- GND
                           |
                        pin ADC

  V_adc = V_motor * R2 / (R1 + R2)

  AJUSTA estos 3 valores según tu circuito real antes de confiar en
  la lectura:
    - VOLT_SENSE_A_PIN / VOLT_SENSE_B_PIN: pines ADC usados
    - R1_OHM, R2_OHM: resistencias del divisor (elige R1/R2 de forma
      que V_adc nunca pase de ~3.0V con el voltaje maximo esperado
      del motor; ej. si el motor puede llegar a 24V, con R2=10k y
      R1=68k: V_adc_max = 24 * 10/(68+10) = 3.08V)

  Si por ahora NO tienes el divisor armado, dejar estos pines
  conectados a nada dará lecturas de voltaje sin sentido (ruido) -
  ignora esa columna hasta que conectes el circuito.
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

// ---------------- Pines de sensado de voltaje (AJUSTAR) ----------------
#define VOLT_SENSE_A_PIN   36
#define VOLT_SENSE_B_PIN   39

// ---------------- Divisor resistivo (AJUSTAR a tu circuito real) ----------------
#define R1_OHM   68000.0
#define R2_OHM   10000.0

// ---------------- Calibración de encoder (ticks/vuelta medidos) ----------------
#define CPR_SALIDA_A  78.3
#define CPR_SALIDA_B  70.2
#define ENCB_SIGN  -1

// ---------------- PWM (LEDC) ----------------
#define PWM_FREQ        20000
#define PWM_RESOLUTION  8

// ---------------- Impresión de telemetría ----------------
#define PRINT_MS   200
#define SPEED_CALC_INTERVAL_MS  150

volatile long encoderA_count = 0;
volatile long encoderB_count = 0;

int pwmActualA = 0;
int pwmActualB = 0;

long lastEncA_forSpeed = 0;
long lastEncB_forSpeed = 0;
unsigned long lastSpeedCalcTime = 0;
unsigned long lastPrintTime = 0;

float speedA_rpm = 0;
float speedB_rpm = 0;


// ==========================================================
//        VARIABLES PARA PROMEDIO DE RPM
// ==========================================================

int pwmPromedioA = 0;
int pwmPromedioB = 0;

float sumaRpmA = 0;
float sumaRpmB = 0;

unsigned long muestrasRpmA = 0;
unsigned long muestrasRpmB = 0;


// ==========================================================
//                  INTERRUPCIÓN ENCODER A
// ==========================================================

void IRAM_ATTR isrEncoderA() {
  if (digitalRead(ENCA_C1) == digitalRead(ENCA_C2)) {
    encoderA_count++;
  } else {
    encoderA_count--;
  }
}


// ==========================================================
//                  INTERRUPCIÓN ENCODER B
// ==========================================================

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
    }
    else if (speed < 0) {
      digitalWrite(AIN1_PIN, LOW);
      digitalWrite(AIN2_PIN, HIGH);
    }
    else {
      digitalWrite(AIN1_PIN, LOW);
      digitalWrite(AIN2_PIN, LOW);
    }

    ledcWrite(PWMA_PIN, pwmVal);

    pwmActualA = speed;

  } else {

    if (speed > 0) {
      digitalWrite(BIN1_PIN, HIGH);
      digitalWrite(BIN2_PIN, LOW);
    }
    else if (speed < 0) {
      digitalWrite(BIN1_PIN, LOW);
      digitalWrite(BIN2_PIN, HIGH);
    }
    else {
      digitalWrite(BIN1_PIN, LOW);
      digitalWrite(BIN2_PIN, LOW);
    }

    ledcWrite(PWMB_PIN, pwmVal);

    pwmActualB = speed;
  }
}


// ==========================================================
//             FUNCIÓN: DETENER TODOS LOS MOTORES
// ==========================================================

void stopAllMotors() {

  setMotor('A', 0);
  setMotor('B', 0);

  digitalWrite(STBY_PIN, LOW);
}


// ==========================================================
//             FUNCIÓN: MOSTRAR PROMEDIO MOTOR A
// ==========================================================

void mostrarPromedioA() {

  if (muestrasRpmA > 0) {

    float promedio = sumaRpmA / muestrasRpmA;

    Serial.print(">>> PROMEDIO A | PWM=");
    Serial.print(pwmPromedioA);
    Serial.print(" | RPM=");
    Serial.println(promedio, 2);
  }

  sumaRpmA = 0;
  muestrasRpmA = 0;
}


// ==========================================================
//             FUNCIÓN: MOSTRAR PROMEDIO MOTOR B
// ==========================================================

void mostrarPromedioB() {

  if (muestrasRpmB > 0) {

    float promedio = sumaRpmB / muestrasRpmB;

    Serial.print(">>> PROMEDIO B | PWM=");
    Serial.print(pwmPromedioB);
    Serial.print(" | RPM=");
    Serial.println(promedio, 2);
  }

  sumaRpmB = 0;
  muestrasRpmB = 0;
}


// ==========================================================
//        FUNCIÓN: CAMBIO DE PWM + PROMEDIO
// ==========================================================

void actualizarPromedioPWM(char motor, int nuevoPWM) {

  if (motor == 'A') {

    // Si cambió el PWM, mostrar el promedio anterior
    if (pwmPromedioA != nuevoPWM && muestrasRpmA > 0) {
      mostrarPromedioA();
    }

    // Comenzar un nuevo promedio
    if (pwmPromedioA != nuevoPWM) {

      pwmPromedioA = nuevoPWM;

      sumaRpmA = 0;
      muestrasRpmA = 0;
    }

  } else {

    // Si cambió el PWM, mostrar el promedio anterior
    if (pwmPromedioB != nuevoPWM && muestrasRpmB > 0) {
      mostrarPromedioB();
    }

    // Comenzar un nuevo promedio
    if (pwmPromedioB != nuevoPWM) {

      pwmPromedioB = nuevoPWM;

      sumaRpmB = 0;
      muestrasRpmB = 0;
    }
  }
}


// ==========================================================
//     FUNCIÓN: LECTURA Y CÁLCULO DE VELOCIDAD (RPM)
// ==========================================================

void updateEncoderSpeeds() {

  unsigned long now = millis();

  unsigned long dt_ms = now - lastSpeedCalcTime;

  if (dt_ms < SPEED_CALC_INTERVAL_MS) return;

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

  speedA_rpm = (deltaA / CPR_SALIDA_A) / dt_min;

  speedB_rpm = (deltaB / CPR_SALIDA_B) / dt_min;


  // --------------------------------------------------------
  // Acumular RPM para el promedio
  // --------------------------------------------------------

  if (pwmActualA != 0) {

    sumaRpmA += speedA_rpm;
    muestrasRpmA++;
  }

  if (pwmActualB != 0) {

    sumaRpmB += speedB_rpm;
    muestrasRpmB++;
  }
}


// ==========================================================
//     FUNCIÓN: LECTURA DE VOLTAJE DEL MOTOR
// ==========================================================

float leerVoltajeMotor(int pinADC) {

  uint32_t mv = analogReadMilliVolts(pinADC);

  float v_adc = mv / 1000.0;

  float v_motor =
    v_adc * (R1_OHM + R2_OHM) / R2_OHM;

  return v_motor;
}


// ==========================================================
//                         SETUP
// ==========================================================

void setup() {

  Serial.begin(115200);

  pinMode(AIN1_PIN, OUTPUT);
  pinMode(AIN2_PIN, OUTPUT);

  pinMode(BIN1_PIN, OUTPUT);
  pinMode(BIN2_PIN, OUTPUT);

  pinMode(STBY_PIN, OUTPUT);


  // PWM
  ledcAttach(PWMA_PIN, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(PWMB_PIN, PWM_FREQ, PWM_RESOLUTION);


  // Encoders
  pinMode(ENCA_C1, INPUT_PULLUP);
  pinMode(ENCA_C2, INPUT_PULLUP);

  pinMode(ENCB_C1, INPUT_PULLUP);
  pinMode(ENCB_C2, INPUT_PULLUP);


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


  analogReadResolution(12);


  stopAllMotors();

  lastSpeedCalcTime = millis();


  Serial.println("=== Control manual de PWM + RPM + Voltaje ===");

  Serial.println("Comandos: A<pwm>  B<pwm>  A0  B0  S");

  Serial.println(
    "Ej: A180   (motor A al 180 de PWM, sigue corriendo)"
  );

  Serial.println(
    "Promedio RPM: se muestra al cambiar de PWM."
  );
}


// ==========================================================
//                          LOOP
// ==========================================================

void loop() {

  // ========================================================
  // Leer comandos
  // ========================================================

  if (Serial.available()) {

    String cmd = Serial.readStringUntil('\n');

    cmd.trim();


    // ------------------------------------------------------
    // DETENER AMBOS
    // ------------------------------------------------------

    if (cmd == "S" || cmd == "s") {

      // Mostrar promedio pendiente
      mostrarPromedioA();
      mostrarPromedioB();

      stopAllMotors();

      Serial.println("# Motores detenidos");
    }


    // ------------------------------------------------------
    // MOTOR A
    // ------------------------------------------------------

    else if (
      cmd.length() >= 1 &&
      (cmd[0] == 'A' || cmd[0] == 'a')
    ) {

      int pwmVal = cmd.substring(1).toInt();

      actualizarPromedioPWM('A', pwmVal);

      setMotor('A', pwmVal);

      Serial.print("# Motor A -> PWM=");
      Serial.println(pwmVal);
    }


    // ------------------------------------------------------
    // MOTOR B
    // ------------------------------------------------------

    else if (
      cmd.length() >= 1 &&
      (cmd[0] == 'B' || cmd[0] == 'b')
    ) {

      int pwmVal = cmd.substring(1).toInt();

      actualizarPromedioPWM('B', pwmVal);

      setMotor('B', pwmVal);

      Serial.print("# Motor B -> PWM=");
      Serial.println(pwmVal);
    }
  }


  // ========================================================
  // Actualizar RPM
  // ========================================================

  updateEncoderSpeeds();


  // ========================================================
  // Telemetría original
  // ========================================================

  if (millis() - lastPrintTime >= PRINT_MS) {

    lastPrintTime = millis();


    // ------------------------------------------------------
    // MOTOR A
    // ------------------------------------------------------

    if (pwmActualA != 0) {

      float vA =
        leerVoltajeMotor(VOLT_SENSE_A_PIN);

      Serial.print("A,");
      Serial.print(pwmActualA);
      Serial.print(",");
      Serial.print(speedA_rpm, 2);
      Serial.print(",");
      Serial.println(vA, 2);
    }


    // ------------------------------------------------------
    // MOTOR B
    // ------------------------------------------------------

    if (pwmActualB != 0) {

      float vB =
        leerVoltajeMotor(VOLT_SENSE_B_PIN);

      Serial.print("B,");
      Serial.print(pwmActualB);
      Serial.print(",");
      Serial.print(speedB_rpm, 2);
      Serial.print(",");
      Serial.println(vB, 2);
    }
  }
}
