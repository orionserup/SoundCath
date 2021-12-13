#include <stdint.h>

#define SEL0 4
#define SEL1 5
#define SEL2 6
#define SEL3 7
#define SEL4 8
#define SEL5 9
#define SEL6 10

#define TRIG0 11
#define TRIG1 12

const uint8_t sel[7] = { SEL0, SEL1, SEL2, SEL3, SEL4, SEL5, SEL6 };
const uint8_t trig[2] = { TRIG0, TRIG1 };

void set_channel(const uint8_t channel);
void set_trigger(const uint8_t trigger);
void reset_trigger(const uint8_t trigger);

void setup() {

  Serial.begin(115200);
  Serial.setTimeout(1);

  for (uint8_t i = 0; i < sizeof(sel); i++)
    pinMode(sel[i], OUTPUT);

  for (uint8_t i = 0; i < sizeof(trig); i++)
    pinMode(trig[i], OUTPUT);

}

void loop() {

  while(!Serial.available());

  int value = Serial.readString().toInt();
  uint8_t channel = abs(value) & 0x3f;

  Serial.println(value);

  set_channel(channel);

}

void set_channel(const uint8_t channel) {

  for (uint8_t i = 0; i < sizeof(sel); i++)
    digitalWrite(sel[i], channel & 1 << i);

}

void set_trigger(const uint8_t trigger) {

  for (uint8_t i = 0; i < sizeof(trig); i++)
    digitalWrite(trig[i], trigger & 1 << i);

}

void reset_trigger(const uint8_t trigger) {

  for (uint8_t i = 0; i < sizeof(trig); i++)
    digitalWrite(trig[i], trigger & ~(1 << i));

}
