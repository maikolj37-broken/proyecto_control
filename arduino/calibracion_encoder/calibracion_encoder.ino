/*
  Calibración de encoder: mide cuántos "ticks" (pulsos ya decodificados
  en cuadratura x4) corresponden a UNA vuelta del EJE DE SALIDA
  (después del gearbox), para usar ese número directamente como
  CPR_SALIDA en el sketch principal, sin depender de datos de datasheet.

  Procedimiento:
  1. Sube este sketch y abre el Monitor Serial (115200 baudios).
  2. Escribe "a" y Enter -> reinicia el contador del motor A a 0.
  3. Gira a mano el eje de salida del motor A LENTAMENTE y EXACTO
     un número entero de vueltas completas (recomendado: 5 a 10 vueltas,
     entre más vueltas midas, menor el error de redondeo). Marca el eje
     con un punto/flecha para no perder la cuenta.
  4. Escribe "ca" seguido del número de vueltas que diste, sin espacio,
     por ejemplo "ca5" si diste 5 vueltas, y presiona Enter.
  5. El monitor imprime los ticks/vuelta del motor A. Repite lo mismo
     para el motor B con "b" y "cb<vueltas>".
  6. Usa el valor impreso (ticks/vuelta) como CPR_SALIDA_A o
     CPR_SALIDA_B en el sketch principal de motores/RPM.
*/

// ---------------- Pines de los encoders ----------------
#define ENCA_C1 23
#define ENCA_C2 22
#define ENCB_C1 18
#define ENCB_C2 5

volatile long countA = 0;
volatile long countB = 0;

void IRAM_ATTR isrEncoderA() {
  if (digitalRead(ENCA_C1) == digitalRead(ENCA_C2)) {
    countA++;
  } else {
    countA--;
  }
}

void IRAM_ATTR isrEncoderB() {
  if (digitalRead(ENCB_C1) == digitalRead(ENCB_C2)) {
    countB++;
  } else {
    countB--;
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(ENCA_C1, INPUT_PULLUP);
  pinMode(ENCA_C2, INPUT_PULLUP);
  pinMode(ENCB_C1, INPUT_PULLUP);
  pinMode(ENCB_C2, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENCA_C1), isrEncoderA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCB_C1), isrEncoderB, CHANGE);

  Serial.println("=== Calibracion de encoder ===");
  Serial.println("Comandos:");
  Serial.println("  a          -> reinicia el contador del motor A a 0");
  Serial.println("  b          -> reinicia el contador del motor B a 0");
  Serial.println("  ca<N>      -> ej: ca5  -> calcula ticks/vuelta de A con N vueltas dadas");
  Serial.println("  cb<N>      -> ej: cb5  -> calcula ticks/vuelta de B con N vueltas dadas");
  Serial.println("  p          -> muestra los conteos actuales sin resetear");
}

void loop() {
  // Muestra el conteo en vivo cada 500 ms, útil para ver que sí detecta pulsos
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 500) {
    lastPrint = millis();
    noInterrupts();
    long a = countA;
    long b = countB;
    interrupts();
    Serial.print("countA=");
    Serial.print(a);
    Serial.print("   countB=");
    Serial.println(b);
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "a") {
      noInterrupts();
      countA = 0;
      interrupts();
      Serial.println(">> Contador A reiniciado a 0. Gira el eje de salida del motor A ahora.");
    } else if (cmd == "b") {
      noInterrupts();
      countB = 0;
      interrupts();
      Serial.println(">> Contador B reiniciado a 0. Gira el eje de salida del motor B ahora.");
    } else if (cmd == "p") {
      noInterrupts();
      long a = countA;
      long b = countB;
      interrupts();
      Serial.print("countA=");
      Serial.print(a);
      Serial.print("  countB=");
      Serial.println(b);
    } else if (cmd.startsWith("ca")) {
      float vueltas = cmd.substring(2).toFloat();
      if (vueltas > 0) {
        noInterrupts();
        long c = countA;
        interrupts();
        float ticksPorVuelta = abs(c) / vueltas;
        Serial.print("Motor A: ");
        Serial.print(c);
        Serial.print(" ticks en ");
        Serial.print(vueltas, 2);
        Serial.print(" vueltas -> ");
        Serial.print(ticksPorVuelta, 2);
        Serial.println(" ticks/vuelta  (usa este numero como CPR_SALIDA_A)");
      } else {
        Serial.println("Formato invalido. Ejemplo correcto: ca5");
      }
    } else if (cmd.startsWith("cb")) {
      float vueltas = cmd.substring(2).toFloat();
      if (vueltas > 0) {
        noInterrupts();
        long c = countB;
        interrupts();
        float ticksPorVuelta = abs(c) / vueltas;
        Serial.print("Motor B: ");
        Serial.print(c);
        Serial.print(" ticks en ");
        Serial.print(vueltas, 2);
        Serial.print(" vueltas -> ");
        Serial.print(ticksPorVuelta, 2);
        Serial.println(" ticks/vuelta  (usa este numero como CPR_SALIDA_B)");
      } else {
        Serial.println("Formato invalido. Ejemplo correcto: cb5");
      }
    }
  }
}
