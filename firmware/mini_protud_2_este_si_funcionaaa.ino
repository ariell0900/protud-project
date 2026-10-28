// =====================================================
// SMARS + Puente H L298N + Bluetooth HC-05
// Motores: 2x Micro Motor N20 12V 1000 rpm
// Alimentacion: bateria de 9V
// Pin digital 3: NO se usa
// App: BT Car Controller (o similar)
//
// Comandos que entiende:
//   F adelante      B atras
//   L izquierda     R derecha
//   G adelante-izq  I adelante-der
//   H atras-izq     J atras-der
//   S parar         D parar todo
//   0..9 y q        velocidad (0 = lento, q = maxima)
//
// No necesita librerias extra.
// =====================================================

#include <SoftwareSerial.h>

// ---------- BLUETOOTH HC-05 ----------
// Pin 2 (RX del Arduino) <- TXD del HC-05
// El RXD del HC-05 NO se conecta: el robot solo recibe ordenes.
// (El pin 8 queda reservado por la libreria, pero sin cable.)
SoftwareSerial bluetooth(2, 8);

// ---------- PUENTE H L298N ----------
// Motor A = oruga izquierda (salida OUT1 / OUT2)
const int ENA = 9;   // velocidad (PWM)
const int IN1 = 4;   // direccion
const int IN2 = 5;   // direccion

// Motor B = oruga derecha (salida OUT3 / OUT4)
const int ENB = 10;  // velocidad (PWM)
const int IN3 = 6;   // direccion
const int IN4 = 7;   // direccion

// Los motores van montados en espejo: si una oruga va al reves, pone true
const bool INVERTIR_IZQ = false;
const bool INVERTIR_DER = false;

// ---------- VELOCIDAD ----------
// Los N20 de 1000 rpm son muy rapidos: arrancamos a velocidad media.
int velocidad = 150;

// Por debajo de este valor el N20 zumba pero no llega a girar
// (con bateria de 9V les llega menos tension, por eso es un poco alto)
const int VEL_MINIMA = 110;

// Rampa: cuanto sube o baja la velocidad cada 10 ms.
// Evita tirones y que el Arduino se reinicie por picos de corriente.
const int PASO_RAMPA = 8;
const unsigned long INTERVALO_RAMPA = 10;

// ---------- FRENO DE SEGURIDAD ----------
// Si pasan estos milisegundos sin recibir nada, se detiene.
// Dejalo en 0 si el robot se frena a los saltitos.
const unsigned long TIEMPO_SEGURIDAD = 0;

// ---------- ESTADO ----------
int objetivoIzq = 0, objetivoDer = 0;   // a donde queremos llegar
int actualIzq = 0, actualDer = 0;       // lo que tienen los motores ahora
unsigned long ultimoComando = 0;
unsigned long ultimaRampa = 0;


// Aplica una potencia a un motor del L298N.
// Positivo = adelante, negativo = atras, 0 = parar
void aplicar(int pinEN, int pinA, int pinB, int potencia, bool invertir) {
  if (invertir) potencia = -potencia;

  if (potencia > 0) {
    digitalWrite(pinA, HIGH);
    digitalWrite(pinB, LOW);
  } else if (potencia < 0) {
    digitalWrite(pinA, LOW);
    digitalWrite(pinB, HIGH);
  } else {
    digitalWrite(pinA, LOW);
    digitalWrite(pinB, LOW);
  }
  analogWrite(pinEN, abs(potencia));
}

void aplicarIzq(int p) { aplicar(ENA, IN1, IN2, p, INVERTIR_IZQ); }
void aplicarDer(int p) { aplicar(ENB, IN3, IN4, p, INVERTIR_DER); }

// Acerca de a poco el valor actual al objetivo
int acercar(int actual, int objetivo) {
  if (actual < objetivo) return min(actual + PASO_RAMPA, objetivo);
  if (actual > objetivo) return max(actual - PASO_RAMPA, objetivo);
  return actual;
}

// Le dice a cada oruga a que velocidad tiene que ir
void orugas(int izq, int der) {
  objetivoIzq = izq;
  objetivoDer = der;
}

void parar() {
  orugas(0, 0);
}


void setup() {
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  bluetooth.begin(9600);

  // El robot siempre arranca detenido
  aplicarIzq(0);
  aplicarDer(0);
}


void loop() {
  // 1) Leer comandos de la app
  if (bluetooth.available()) {
    char comando = bluetooth.read();
    int v = velocidad;
    int lenta = max(v / 3, VEL_MINIMA);  // oruga lenta en las diagonales
    if (lenta > v) lenta = v;

    switch (comando) {
      case 'F': orugas( v,  v);          break;  // adelante
      case 'B': orugas(-v, -v);          break;  // atras
      case 'L': orugas(-v,  v);          break;  // gira a la izquierda en el lugar
      case 'R': orugas( v, -v);          break;  // gira a la derecha en el lugar
      case 'G': orugas( lenta,  v);      break;  // adelante doblando a la izquierda
      case 'I': orugas( v,  lenta);      break;  // adelante doblando a la derecha
      case 'H': orugas(-lenta, -v);      break;  // atras hacia la izquierda
      case 'J': orugas(-v, -lenta);      break;  // atras hacia la derecha
      case 'S':
      case 'D': parar();                 break;
      case 'q': velocidad = 255;         break;
      default:
        if (comando >= '0' && comando <= '9') {
          // '0' -> VEL_MINIMA, '9' -> 255
          velocidad = map(comando - '0', 0, 9, VEL_MINIMA, 255);
        } else {
          comando = 0;  // ignora luces, bocina, saltos de linea, etc.
        }
    }
    if (comando != 0) ultimoComando = millis();
  }

  // 2) Freno de seguridad
  if (TIEMPO_SEGURIDAD > 0 && millis() - ultimoComando > TIEMPO_SEGURIDAD) {
    parar();
  }

  // 3) Rampa: mover los motores de a poco hacia el objetivo
  if (millis() - ultimaRampa >= INTERVALO_RAMPA) {
    ultimaRampa = millis();

    int nuevoIzq = acercar(actualIzq, objetivoIzq);
    int nuevoDer = acercar(actualDer, objetivoDer);

    if (nuevoIzq != actualIzq) {
      actualIzq = nuevoIzq;
      aplicarIzq(actualIzq);
    }
    if (nuevoDer != actualDer) {
      actualDer = nuevoDer;
      aplicarDer(actualDer);
    }
  }
}
