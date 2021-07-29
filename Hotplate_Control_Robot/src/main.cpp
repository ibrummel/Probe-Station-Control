#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MAX31856.h>
#include <Servo.h>
#include "interface.h"

// Use software SPI: CS, DI, DO, CLK
//Adafruit_MAX31856 maxthermo = Adafruit_MAX31856(10, 11, 12, 13);
// use hardware SPI, just pass in the CS pin
Adafruit_MAX31856 maxthermo = Adafruit_MAX31856(A2);
// use hardware SPI, pass in the CS pin and using SPI1
//Adafruit_MAX31856 maxthermo = Adafruit_MAX31856(10, &SPI1);
bool dataReady = false;
bool fault = false;
Servo tKnob1;
Servo tKnob2;
int pos = 0;
float lastTemp = -100;

void moveDoubleServo(int pos){
  tKnob1.write(pos);
  tKnob2.write(pos);
}

int readDoubleServo(){
  int pos1, pos2;
  pos1 = tKnob1.read();
  pos2 = tKnob2.read();

  if (pos1 != pos2) {
    tKnob2.write(pos1);
  }

  return pos1;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  pinMode(A1, INPUT); // Fault Pin
  pinMode(A0, INPUT); // Data Ready
  tKnob1.attach(A10); // Colored Silver, left servo
  tKnob2.attach(A9);  // Not colored, Right servo

  if (!maxthermo.begin()) {
    Serial.println("<Could not initialize thermocouple.>");
    while (1) delay(10);
  }

  maxthermo.setThermocoupleType(MAX31856_TCTYPE_K);

  // Serial.print("Thermocouple type: ");
  // switch (maxthermo.getThermocoupleType() ) {
  //   case MAX31856_TCTYPE_B: Serial.println("B Type"); break;
  //   case MAX31856_TCTYPE_E: Serial.println("E Type"); break;
  //   case MAX31856_TCTYPE_J: Serial.println("J Type"); break;
  //   case MAX31856_TCTYPE_K: Serial.println("K Type"); break;
  //   case MAX31856_TCTYPE_N: Serial.println("N Type"); break;
  //   case MAX31856_TCTYPE_R: Serial.println("R Type"); break;
  //   case MAX31856_TCTYPE_S: Serial.println("S Type"); break;
  //   case MAX31856_TCTYPE_T: Serial.println("T Type"); break;
  //   case MAX31856_VMODE_G8: Serial.println("Voltage x8 Gain mode"); break;
  //   case MAX31856_VMODE_G32: Serial.println("Voltage x32 Gain mode"); break;
  //   default: Serial.println("Unknown"); break;
  // }

  // Diagnostic Motor Spin on start.
  // moveDoubleServo(0.0);
  // delay(200);
  // moveDoubleServo(180);

  delay(200);

  maxthermo.setConversionMode(MAX31856_ONESHOT_NOWAIT);
}

void loop() {
  // trigger a conversion, returns immediately
  maxthermo.triggerOneShot();

  // check for conversion complete and read temperature
  dataReady = !digitalRead(A0);
  fault = digitalRead(A1);
  if (dataReady) {
    lastTemp = maxthermo.readThermocoupleTemperature();
  } 
  else if (!fault) {
    Serial.print("<Read Fault:\t");
          uint8_t fault = maxthermo.readFault();
      if (fault) {
        if (fault & MAX31856_FAULT_CJRANGE) Serial.println("Cold Junction Range Fault>");
        if (fault & MAX31856_FAULT_TCRANGE) Serial.println("Thermocouple Range Fault>");
        if (fault & MAX31856_FAULT_CJHIGH)  Serial.println("Cold Junction High Fault>");
        if (fault & MAX31856_FAULT_CJLOW)   Serial.println("Cold Junction Low Fault>");
        if (fault & MAX31856_FAULT_TCHIGH)  Serial.println("Thermocouple High Fault>");
        if (fault & MAX31856_FAULT_TCLOW)   Serial.println("Thermocouple Low Fault>");
        if (fault & MAX31856_FAULT_OVUV)    Serial.println("Over/Under Voltage Fault>");
        if (fault & MAX31856_FAULT_OPEN)    Serial.println("Thermocouple Open Fault>");
      }
  }

  delay(100);
  recieve();
  if (newData) {
    parse();

    // Serial.println("DEBUG:");
    // Serial.print("Axis: |");
    // Serial.print(axis);
    // Serial.print("|\t Value: ");
    // Serial.println(value);

    if (commandType == QUERY){
      if (axis == 'p') {
        char charInt[7];
        itoa(readDoubleServo(), charInt, 10);
        respond(charInt);
      }
      else if (axis == 't') {
        char charFloat[7];
        dtostrf(lastTemp, 6, 2, charFloat);
        respond(charFloat);
      }
    }
    else if (commandType == COMMAND) {
      if (axis == 'p') {
        moveDoubleServo(value);
      }
    }

    commandType = NONE;
    newData = false;
  }
}