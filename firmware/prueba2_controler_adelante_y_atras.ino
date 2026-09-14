#include <SoftwareSerial.h>

// ========================
// BLUETOOTH HC-05
// ========================

// Arduino RX = 2  <- TX del HC-05
// Arduino TX = 8  -> RX del HC-05
SoftwareSerial bluetooth(2, 8);

// ========================
// L298N
// ========================

// Motor A
const int ENA = 9;
const int IN1 = 4;
const int IN2 = 5;

// Motor B
const int ENB = 10;
const int IN3 = 6;
const int IN4 = 7;

// Velocidad: 0 - 255
const int velocidad = 180;


// ========================
// DETENER
// ========================

void parar() {

  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}


// ========================
// ADELANTE
// ========================

void adelante() {

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, velocidad);
  analogWrite(ENB, velocidad);
}


// ========================
// ATRÁS
// ========================

void atras() {

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, velocidad);
  analogWrite(ENB, velocidad);
}


// ========================
// SETUP
// ========================

void setup() {

  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  bluetooth.begin(9600);

  // IMPORTANTE:
  // El robot siempre arranca detenido.
  parar();
}


// ========================
// LOOP
// ========================

void loop() {

  if (bluetooth.available()) {

    char comando = bluetooth.read();

    if (comando == 'F') {
      adelante();
    }

    else if (comando == 'B') {
      atras();
    }

    else if (comando == 'S') {
      parar();
    }
  }
}
