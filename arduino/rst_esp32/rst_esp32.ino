#include <Arduino.h>
#include <math.h>

// =====================================================================
// LAB 6 - RST discreto en ESP32 (Motor A izquierdo, Motor B derecho)
// Ley de control:  u(k) = u(k-1) + t0*r(k-1) - r0*y(k) - r1*y(k-1)
// Los coeficientes se calculan solos en setup() a partir de K, tau y TS.
// Comandos por Serial:  G = iniciar experimento   S = parar
// =====================================================================

// ---------- PINES (los mismos de tu codigo de pruebas) ----------
const int PIN_PWM_A = 25, PIN_IN1_A = 26, PIN_IN2_A = 27, PIN_ENC_A = 34;
const int PIN_PWM_B = 14, PIN_IN1_B = 12, PIN_IN2_B = 13, PIN_ENC_B = 35;

// ---------- PARAMETROS DEL DISENO (iguales a la simulacion) ----------
const double TS      = 0.05;   // periodo de muestreo [s]
const double ZETA    = 0.8;
const double KTS     = 0.6;    // ts deseado = 0.6 * ts lazo abierto

// ---------- EXPERIMENTO (igual al de Simulink) ----------
const double REF_RPM  = 50.0;  // escalon de referencia [rpm]
const double T_REF    = 0.5;   // instante del escalon de referencia [s]
const double T_DIST   = 3.5;   // instante de la perturbacion [s]
const double DIST_PWM = -15.0; // perturbacion sumada al PWM (como en Simulink)
const double T_FIN    = 6.0;   // duracion total [s]

// ---------- ENCODER ----------
const float PPR_TOTALES = 330.0;
volatile long pulsosA = 0, pulsosB = 0;
void IRAM_ATTR ISR_EncoderA() { pulsosA++; }
void IRAM_ATTR ISR_EncoderB() { pulsosB++; }

// ---------- MOTOR + CONTROLADOR ----------
struct Motor {
  int pinPWM, pinIN1, pinIN2;
  double K, tau;              // planta identificada
  double r0, r1, t0;          // coeficientes RST (se calculan en disenar())
  double uPrev, yPrev, rPrev; // memoria del controlador
};

//            PWM  IN1  IN2   K       tau     r0 r1 t0  uPrev yPrev rPrev
Motor motores[2] = {
  { PIN_PWM_A, PIN_IN1_A, PIN_IN2_A, 0.7857, 0.4191, 0, 0, 0, 0, 0, 0 },  // Motor A (izq)
  { PIN_PWM_B, PIN_IN1_B, PIN_IN2_B, 0.7642, 0.4981, 0, 0, 0, 0, 0, 0 }   // Motor B (der)
};

bool corriendo = false;
unsigned long tSiguiente = 0;   // proximo instante de muestreo [us]
long k = 0;                     // contador de muestras

// Diseno RST por asignacion de polos (misma formula que en MATLAB)
void disenar(int i) {
  Motor &m = motores[i];
  double a1 = -exp(-TS / m.tau);
  double b1 = m.K * (1.0 - exp(-TS / m.tau));
  double wn = 4.0 / (ZETA * KTS * 4.0 * m.tau);
  double sigma = ZETA * wn;
  double wd = wn * sqrt(1.0 - ZETA * ZETA);
  double p1 = -2.0 * exp(-sigma * TS) * cos(wd * TS);
  double p0 = exp(-2.0 * sigma * TS);
  m.r0 = (p1 - a1 + 1.0) / b1;
  m.r1 = (p0 + a1) / b1;
  m.t0 = (1.0 + p1 + p0) / b1;
}

void adelante(int i) {
  Motor &m = motores[i];
  digitalWrite(m.pinIN1, HIGH);
  digitalWrite(m.pinIN2, LOW);
}

void parar() {
  corriendo = false;
  for (int i = 0; i < 2; i++) {
    analogWrite(motores[i].pinPWM, 0);
    digitalWrite(motores[i].pinIN1, LOW);
    digitalWrite(motores[i].pinIN2, LOW);
  }
}

// Un paso del controlador: devuelve u (antes de la perturbacion)
double pasoRST(int i, double r, double y, double dist) {
  Motor &m = motores[i];
  double u = m.uPrev + m.t0 * m.rPrev - m.r0 * y - m.r1 * m.yPrev;
  u = constrain(u, 0.0, 255.0);              // saturacion + anti-windup
  analogWrite(m.pinPWM, (int)round(constrain(u + dist, 0.0, 255.0)));
  m.uPrev = u;  m.yPrev = y;  m.rPrev = r;
  return u;
}

void iniciar() {
  for (int i = 0; i < 2; i++) {
    motores[i].uPrev = 0; motores[i].yPrev = 0; motores[i].rPrev = 0;
  }
  noInterrupts(); pulsosA = 0; pulsosB = 0; interrupts();
  adelante(0); adelante(1);
  k = 0;
  Serial.println("#INICIO");
  Serial.println("t,rA,yA,uA,rB,yB,uB");
  tSiguiente = micros() + (unsigned long)(TS * 1e6);
  corriendo = true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(PIN_IN1_A, OUTPUT); pinMode(PIN_IN2_A, OUTPUT); pinMode(PIN_PWM_A, OUTPUT);
  pinMode(PIN_IN1_B, OUTPUT); pinMode(PIN_IN2_B, OUTPUT); pinMode(PIN_PWM_B, OUTPUT);
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), ISR_EncoderA, RISING);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), ISR_EncoderB, RISING);

  disenar(0);
  disenar(1);
  parar();

  Serial.println("#--- RST ESP32 ---");
  Serial.printf("#Motor A: t0=%.4f r0=%.4f r1=%.4f\n", motores[0].t0, motores[0].r0, motores[0].r1);
  Serial.printf("#Motor B: t0=%.4f r0=%.4f r1=%.4f\n", motores[1].t0, motores[1].r0, motores[1].r1);
  Serial.println("#Envia G para iniciar, S para parar");
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'G' || c == 'g') iniciar();
    if (c == 'S' || c == 's') { parar(); Serial.println("#PARADO"); }
  }
  if (!corriendo) return;

  if ((long)(micros() - tSiguiente) < 0) return;   // aun no toca muestrear
  tSiguiente += (unsigned long)(TS * 1e6);

  // --- leer encoders (pulsos en este periodo) ---
  noInterrupts();
  long pA = pulsosA, pB = pulsosB;
  pulsosA = 0; pulsosB = 0;
  interrupts();
  double yA = (pA / PPR_TOTALES) * (60.0 / TS);   // rpm
  double yB = (pB / PPR_TOTALES) * (60.0 / TS);

  // --- referencia y perturbacion segun el tiempo ---
  double t    = k * TS;
  double r    = (t >= T_REF)  ? REF_RPM  : 0.0;
  double dist = (t >= T_DIST) ? DIST_PWM : 0.0;

  // --- controladores ---
  double uA = pasoRST(0, r, yA, dist);
  double uB = pasoRST(1, r, yB, dist);

  Serial.printf("%.2f,%.1f,%.2f,%.2f,%.1f,%.2f,%.2f\n", t, r, yA, uA, r, yB, uB);

  k++;
  if (t >= T_FIN) {
    parar();
    Serial.println("#FIN");
  }
}
