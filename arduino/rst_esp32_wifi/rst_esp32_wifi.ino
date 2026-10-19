#include <Arduino.h>
#include <math.h>
#include <WiFi.h>
#include <WebServer.h>

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
// WiFi: red "MotorTest" (clave motores123) -> abrir http://192.168.4.1/
//       La pagina inicia el ensayo y grafica los dos motores en vivo.
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

// ---------- WIFI (punto de acceso) ----------
const char* WIFI_SSID     = "MotorTest";
const char* WIFI_PASSWORD = "motores123";
WebServer server(80);

// ---------- BUFFER DE DATOS DEL ENSAYO ----------
struct Fila { float t, r, yA, uA, rpmA, yB, uB, rpmB; };
const int MAX_FILAS = 130;          // T_FIN/TS + 1 = 121 filas
Fila datos[MAX_FILAS];
volatile int nFilas = 0;

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

void iniciar();   // declaracion adelantada

// =====================================================================
//                         PAGINA WEB
// =====================================================================
const char PAGINA[] PROGMEM = R"HTML(
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RST Motores</title>
<style>
body{font-family:sans-serif;margin:0;padding:12px;background:#f4f4f4;color:#222}
h2{margin:6px 0}
button,a.b{font-size:16px;padding:10px 18px;margin:4px;border:none;border-radius:8px;
 color:#fff;text-decoration:none;display:inline-block;cursor:pointer}
.go{background:#16a34a}.st{background:#dc2626}.dl{background:#2563eb}
canvas{width:100%;background:#fff;border:1px solid #ccc;border-radius:6px;margin-bottom:8px}
table{border-collapse:collapse;background:#fff;margin:6px 0}
td,th{border:1px solid #ccc;padding:5px 10px;text-align:center}
.ok{color:#16a34a;font-weight:bold}.no{color:#dc2626;font-weight:bold}
#estado{margin:4px;font-weight:bold}
</style></head><body>
<h2>Controlador RST - Motor A (izq) y Motor B (der)</h2>
<button class="go" onclick="iniciar()">Iniciar ensayo</button>
<button class="st" onclick="fetch('/parar')">Parar</button>
<a class="b dl" href="/datos.csv">Descargar CSV</a>
<div id="estado">Listo.</div>
<canvas id="c1" height="240"></canvas>
<canvas id="c2" height="240"></canvas>
<canvas id="c3" height="240"></canvas>
<div id="tabla"></div>
<script>
let rows=[], cfg=null;
const COL={A:'#2563eb',B:'#dc2626',R:'#6b7280'};

function plot(id,titulo,series){
  const c=document.getElementById(id);
  const W=c.width=c.clientWidth, H=c.height=240, g=c.getContext('2d');
  g.clearRect(0,0,W,H);
  const L=52,Rm=10,T=24,B=26, xmax=cfg?cfg.tfin:6;
  let ymax=0.001;
  series.forEach(s=>s.y.forEach(v=>{if(v>ymax)ymax=v}));
  ymax*=1.1;
  const X=t=>L+(W-L-Rm)*t/xmax, Y=v=>H-B-(H-B-T)*v/ymax;
  g.font='12px sans-serif'; g.fillStyle='#222'; g.strokeStyle='#ddd';
  for(let i=0;i<=5;i++){const v=ymax*i/5;g.beginPath();g.moveTo(L,Y(v));g.lineTo(W-Rm,Y(v));g.stroke();
    g.fillText(v.toFixed(ymax>50?0:2),4,Y(v)+4);}
  for(let t=0;t<=xmax;t++){g.beginPath();g.moveTo(X(t),T);g.lineTo(X(t),H-B);g.stroke();g.fillText(t+'s',X(t)-8,H-8);}
  if(cfg){g.strokeStyle='#f59e0b';g.setLineDash([4,4]);g.beginPath();
    g.moveTo(X(cfg.tdist),T);g.lineTo(X(cfg.tdist),H-B);g.stroke();g.setLineDash([]);
    g.fillStyle='#f59e0b';g.fillText('perturbacion',X(cfg.tdist)+3,T+10);}
  g.fillStyle='#222';g.font='bold 13px sans-serif';g.fillText(titulo,L,14);
  let lx=L+200;
  series.forEach(s=>{
    g.strokeStyle=s.color;g.lineWidth=2;g.setLineDash(s.dash?[6,4]:[]);g.beginPath();
    s.y.forEach((v,i)=>{const x=X(rows[i][0]),y=Y(v);i?g.lineTo(x,y):g.moveTo(x,y)});g.stroke();
    g.setLineDash([]);g.lineWidth=1;g.fillStyle=s.color;g.fillRect(lx,6,14,4);
    g.fillStyle='#222';g.fillText(s.name,lx+18,12);lx+=90;});
}

function dibujar(){
  const col=k=>rows.map(r=>r[k]);
  plot('c1','Velocidad (V equivalentes)',[
    {name:'ref',y:col(1),color:COL.R,dash:1},
    {name:'Motor A',y:col(2),color:COL.A},{name:'Motor B',y:col(5),color:COL.B}]);
  plot('c2','Senal de control u (V)',[
    {name:'Motor A',y:col(3),color:COL.A},{name:'Motor B',y:col(6),color:COL.B}]);
  plot('c3','Velocidad (rpm)',[
    {name:'Motor A',y:col(4),color:COL.A},{name:'Motor B',y:col(7),color:COL.B}]);
}

function metr(col){
  const r=cfg.ref, pre=rows.filter(x=>x[0]>=cfg.tref&&x[0]<cfg.tdist);
  if(pre.length<5) return null;
  const ys=pre.map(x=>x[col]);
  const Mp=Math.max(0,(Math.max(...ys)-r)/r*100);
  const yf=ys.slice(-5).reduce((a,b)=>a+b)/5;
  const ess=Math.abs(r-yf)/r*100;
  let ts=0;
  for(let i=ys.length-1;i>=0;i--){ if(Math.abs(ys[i]-r)>0.02*r){ts=(i+1)*cfg.ts;break;} }
  return {Mp,ess,ts};
}

function tabla(){
  const mA=metr(2), mB=metr(5);
  if(!mA||!mB){document.getElementById('tabla').innerHTML='';return;}
  const f=(v,lim)=>'<td class="'+(v<=lim?'ok':'no')+'">'+v.toFixed(2)+'</td>';
  document.getElementById('tabla').innerHTML=
   '<table><tr><th></th><th>ts [s]</th><th>Mp [%]</th><th>essp [%]</th></tr>'+
   '<tr><th>Limite A</th><td>'+cfg.tsA.toFixed(3)+'</td><td>4.0</td><td>1.0</td></tr>'+
   '<tr><th>Motor A</th>'+f(mA.ts,cfg.tsA)+f(mA.Mp,4)+f(mA.ess,1)+'</tr>'+
   '<tr><th>Limite B</th><td>'+cfg.tsB.toFixed(3)+'</td><td>4.0</td><td>1.0</td></tr>'+
   '<tr><th>Motor B</th>'+f(mB.ts,cfg.tsB)+f(mB.Mp,4)+f(mB.ess,1)+'</tr></table>';
}

async function poll(){
  try{
    const d=await (await fetch('/datos?desde='+rows.length)).json();
    cfg=d.cfg; rows=rows.concat(d.f); dibujar();
    if(d.run){document.getElementById('estado').textContent='Ensayo en curso... t = '+
        (rows.length?rows[rows.length-1][0].toFixed(2):'0')+' s'; setTimeout(poll,400);}
    else{document.getElementById('estado').textContent=rows.length?'Ensayo terminado ('+rows.length+' muestras).':'Listo.';
        tabla();}
  }catch(e){document.getElementById('estado').textContent='Sin conexion con el ESP32';}
}
async function iniciar(){ rows=[]; await fetch('/start'); poll(); }
window.onload=poll;
</script></body></html>
)HTML";

void handleRoot() { server.send(200, "text/html", PAGINA); }

void handleStart() {
  if (!corriendo) iniciar();
  server.send(200, "text/plain", "ok");
}

void handleParar() {
  parar();
  server.send(200, "text/plain", "ok");
}

// JSON incremental: devuelve las filas desde el indice "desde"
void handleDatos() {
  int desde = server.hasArg("desde") ? server.arg("desde").toInt() : 0;
  if (desde < 0) desde = 0;
  int n = nFilas;
  int hasta = n;
  if (hasta - desde > 60) hasta = desde + 60;     // limite por respuesta

  String j;
  j.reserve(4096);
  j += "{\"run\":"; j += (corriendo ? "1" : "0");
  j += ",\"cfg\":{\"ref\":"; j += String(REF_V, 3);
  j += ",\"tref\":"; j += String(T_REF, 2);
  j += ",\"tdist\":"; j += String(T_DIST, 2);
  j += ",\"tfin\":"; j += String(T_FIN, 2);
  j += ",\"ts\":"; j += String(TS, 3);
  j += ",\"tsA\":"; j += String(0.7 * 4.0 * motores[0].tau, 3);
  j += ",\"tsB\":"; j += String(0.7 * 4.0 * motores[1].tau, 3);
  j += "},\"f\":[";
  for (int i = desde; i < hasta; i++) {
    if (i > desde) j += ",";
    j += "["; j += String(datos[i].t, 2);
    j += ","; j += String(datos[i].r, 2);
    j += ","; j += String(datos[i].yA, 3);
    j += ","; j += String(datos[i].uA, 3);
    j += ","; j += String(datos[i].rpmA, 1);
    j += ","; j += String(datos[i].yB, 3);
    j += ","; j += String(datos[i].uB, 3);
    j += ","; j += String(datos[i].rpmB, 1);
    j += "]";
  }
  j += "]}";
  server.send(200, "application/json", j);
}

void handleCSV() {
  String c;
  c.reserve(9000);
  c += "t,rA,yA,uA,rpmA,rB,yB,uB,rpmB\n";
  int n = nFilas;
  for (int i = 0; i < n; i++) {
    c += String(datos[i].t, 2);   c += ",";
    c += String(datos[i].r, 2);   c += ",";
    c += String(datos[i].yA, 3);  c += ",";
    c += String(datos[i].uA, 3);  c += ",";
    c += String(datos[i].rpmA, 1); c += ",";
    c += String(datos[i].r, 2);   c += ",";
    c += String(datos[i].yB, 3);  c += ",";
    c += String(datos[i].uB, 3);  c += ",";
    c += String(datos[i].rpmB, 1); c += "\n";
  }
  server.sendHeader("Content-Disposition", "attachment; filename=motores_real.csv");
  server.send(200, "text/csv", c);
}

void iniciar() {
  for (int i = 0; i < 2; i++) {
    motores[i].uPrev = 0; motores[i].yPrev = 0; motores[i].rPrev = 0;
  }
  noInterrupts(); cuentasA = 0; cuentasB = 0; interrupts();
  digitalWrite(STBY_PIN, HIGH);
  adelante(0); adelante(1);
  k = 0;
  nFilas = 0;
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

  WiFi.softAP(WIFI_SSID, WIFI_PASSWORD);
  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/parar", handleParar);
  server.on("/datos", handleDatos);
  server.on("/datos.csv", handleCSV);
  server.begin();
  Serial.println("#WiFi: red MotorTest (clave motores123) -> http://192.168.4.1/");

  Serial.println("#--- RST ESP32 (TB6612) ---");
  Serial.printf("#Motor A: t0=%.4f r0=%.4f r1=%.4f\n", motores[0].t0, motores[0].r0, motores[0].r1);
  Serial.printf("#Motor B: t0=%.4f r0=%.4f r1=%.4f\n", motores[1].t0, motores[1].r0, motores[1].r1);
  Serial.println("#Envia G para iniciar, S para parar");
}

void loop() {
  server.handleClient();
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

  if (k < MAX_FILAS) {
    datos[k] = { (float)t, (float)r, (float)yA, (float)uA, (float)rpmA,
                 (float)yB, (float)uB, (float)rpmB };
    nFilas = k + 1;
  }

  Serial.printf("%.2f,%.2f,%.3f,%.3f,%.1f,%.2f,%.3f,%.3f,%.1f\n",
                t, r, yA, uA, rpmA, r, yB, uB, rpmB);

  k++;
  if (t >= T_FIN) {
    parar();
    Serial.println("#FIN");
  }
}
