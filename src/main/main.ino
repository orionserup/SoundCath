#include <stdint.h>

#define SEL0 17 // all of the select pins for choosing a channel
#define SEL1 18
#define SEL2 6
#define SEL3 7
#define SEL4 22
#define SEL5 14
#define SEL6 19
#define SEL7 11

#define EN 13 // enable pin

const uint8_t sel[] = { SEL0, SEL1, SEL2, SEL3, SEL4, SEL5, SEL6, SEL7 }; // all of the selct pins

void set_channel(const uint8_t channel);

void setup() {

  Serial.begin(115200); // begin the serial port and 
  Serial.setTimeout(1);

  for (uint8_t i = 0; i < sizeof(sel); i++) // configure all of the select pins as outputs
    pinMode(sel[i], OUTPUT);

  pinMode(EN, OUTPUT); // enable is an output

  digitalWrite(EN, LOW); // disable the device by default

}

void loop() {

  while(!Serial.available()); // wait for the host to send something over the serial port

  int value = Serial.read(); // get the value the host sent

  Serial.println(value); // print the value over the serial port

  set_channel(value); // set the cooresponding channel
  digitalWrite(EN, HIGH); // enable the chip



}

void set_channel(const uint8_t channel) {

  for (uint8_t i = 0; i < sizeof(sel); i++)
    digitalWrite(sel[i], channel & (1 << i)); // set the channel bit by bit 

}

