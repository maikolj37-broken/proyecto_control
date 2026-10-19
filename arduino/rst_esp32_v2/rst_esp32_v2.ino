#include <Arduino.h>
#include <math.h>

// =====================================================================
// LAB 6 - RST discreto en ESP32 + TB6612   (A = izquierdo, B = derecho)
// Ley de control:  u(k) = u(k-1) + t0*r(k-1) - r0*y(k) - r1*y(k-1)
//
// UNIDADES (iguales a tu identificacion):
//   u = voltaje PWM [V]            = pwm/255 * V_ALIMENTACION
//   y = voltaje equivalente [V]    = rpm / K_RPM_POR_V
//   r = referencia en voltaje equivalente [V]
//
// Comandos por Serial:  G = iniciar experimento   S = parar
// =====================================================================

// ---------- PINES TB6612 (iguales a tu codigo de identificacion) ----------
#define PWMA_PIN 14
#define AIN1_PIN 26
#define AIN2_PIN 27
#define STBY_PIN 25
#define PWMB_PIN 13
#define BIN1_PIN 33
#define BIN2_PIN 32

// ---------- ENCODERS (se cuenta cada flanco del canal C1) ----------
#define ENCA_C1 18
#define ENCB_C1 23
const double CPR_A = 69.8;     // cuentas por vuelta de salida
const double CPR_B = 78.3;

// ---------- CALIBRACION ----------
const double V_ALIM   = 4.81;    // alimentacion [V]
const double K_RPM_V_A = 516.1;  // rpm por voltio equivalente
const double K_RPM_V_B = 413.1;
#define PWM_FREQ 20000
#define PWM_RES  8

// ---------- PARAMETROS DEL DISENO (iguales a la simulacion) ----------
const double TS   = 0.05;   // periodo de muestreo [s]
const double ZETA = 0.8;
const double KTS  = 0.6;    // ts deseado = 0.6 * ts lazo abierto

// ---------- EXPERIMENTO (misma forma que en Simulink) ----------
const double REF_V   = 2.5;   // escalon de referencia [V equivalentes] (~1290 rpm en A)
const double T_REF   = 0.5;   // instante del escalon [s]
const double T_DIST  = 3.5;   // instante de la perturbacion [s]
const double DIST_V  = -0.5;  // perturbacion sumada al voltaje aplicado [V]
const double T_FIN   = 6.0;   // duracion total [s]

// ---------- ENCODER (conteo de flancos) ----------
volatile unsigned long cuentasA = 0, cuentasB = 0;
void IRAM_ATTR isrA() { cuentasA++; }
void IRAM_ATTR isrB() { cuentasB++; }

// ---------- MOTOR + CONTROLADOR ----------
struct Motor {
  int pinPWM, pinIN1, pinIN2;
  double K, tau;               // planta identificada
  double kRpmV, cpr;           // calibracion de velocidad
  double r0, r1, t0;           // coeficientes RST (se calculan en disenar())
  double uPrev, yPrev, rPrev;  // memoria del controlador
};

Motor motores[2] = {
  // PWM       IN1       IN2       K       tau     kRpmV      cpr    r0 r1 t0  u y r
  { PWMA_PIN, AIN1_PIN, AIN2_PIN, 0.7857, 0.4191, K_RPM_V_A, CPR_A, 0, 0, 0, 0, 0, 0 },  // A (izq)
  { PWMB_PIN, BIN1_PIN, BIN2_PIN, 0.7642, 0.4981, K_RPM_V_B, CPR_B, 0, 0, 0, 0, 0, 0 }   // B (der)
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
  digitalWrite(motores[i].pinIN1, HIGH);
  digitalWrite(motores[i].pinIN2, LOW);
}

void parar() {
  corriendo = false;
  for (int i = 0; i < 2; i++) {
    ledcWrite(motores[i].pinPWM, 0);
    digitalWrite(motores[i].pinIN1, LOW);
    digitalWrite(motores[i].pinIN2, LOW);
  }
  digitalWrite(STBY_PIN, LOW);
}

// Un paso del controlador. Devuelve u [V] (antes de la perturbacion).
double pasoRST(int i, double r, double y, double distV) {
  Motor &m = motores[i];
  double u = m.uPrev + m.t0 * m.rPrev - m.r0 * y - m.r1 * m.yPrev;
  u = constrain(u, 0.0, V_ALIM);                 // saturacion + anti-windup
  double uAplicado = constrain(u + distV, 0.0, V_ALIM);
  int pwm = (int)round(uAplicado / V_ALIM * 255.0);
  ledcWrite(m.pinPWM, pwm);
  m.uPrev = u;  m.yPrev = y;  m.rPrev = r;
  return u;
}

void iniciar() {
  for (int i = 0; i < 2; i++) {
    motores[i].uPrev = 0; motores[i].yPrev = 0; motores[i].rPrev = 0;
  }
  noInterrupts(); cuentasA = 0; cuentasB = 0; interrupts();
  digitalWrite(STBY_PIN, HIGH);
  adelante(0); adelante(1);
  k = 0;
  Serial.println("#INICIO");
  Serial.println("t,rA,yA,uA,rpmA,rB,yB,uB,rpmB");
  tSiguiente = micros() + (unsigned long)(TS * 1e6);
  corriendo = true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(AIN1_PIN, OUTPUT); pinMode(AIN2_PIN, OUTPUT);
  pinMode(BIN1_PIN, OUTPUT); pinMode(BIN2_PIN, OUTPUT);
  pinMode(STBY_PIN, OUTPUT);
  ledcAttach(PWMA_PIN, PWM_FREQ, PWM_RES);
  ledcAttach(PWMB_PIN, PWM_FREQ, PWM_RES);

  pinMode(ENCA_C1, INPUT_PULLUP);
  pinMode(ENCB_C1, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCA_C1), isrA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCB_C1), isrB, CHANGE);

  disenar(0);
  disenar(1);
  parar();

  Serial.println("#--- RST ESP32 (TB6612) ---");
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

  // --- leer encoders: cuentas en este periodo -> rpm -> voltaje equivalente ---
  noInterrupts();
  unsigned long cA = cuentasA, cB = cuentasB;
  cuentasA = 0; cuentasB = 0;
  interrupts();
  double rpmA = (cA / motores[0].cpr) * (60.0 / TS);
  double rpmB = (cB / motores[1].cpr) * (60.0 / TS);
  double yA = rpmA / motores[0].kRpmV;
  double yB = rpmB / motores[1].kRpmV;

  // --- referencia y perturbacion segun el tiempo ---
  double t     = k * TS;
  double r     = (t >= T_REF)  ? REF_V  : 0.0;
  double distV = (t >= T_DIST) ? DIST_V : 0.0;

  // --- controladores ---
  double uA = pasoRST(0, r, yA, distV);
  double uB = pasoRST(1, r, yB, distV);

  Serial.printf("%.2f,%.2f,%.3f,%.3f,%.1f,%.2f,%.3f,%.3f,%.1f\n",
                t, r, yA, uA, rpmA, r, yB, uB, rpmB);

  k++;
  if (t >= T_FIN) {
    parar();
    Serial.println("#FIN");
  }
}
