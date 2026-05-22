#include <AFMotor.h>

#define MOTOR_SPEED 170

AF_DCMotor M1(1);
AF_DCMotor M2(2);
AF_DCMotor M3(3);
AF_DCMotor M4(4);

char value;

void setup() {
  Serial.begin(9600);
  M1.setSpeed(MOTOR_SPEED);
  M2.setSpeed(MOTOR_SPEED);
  M3.setSpeed(MOTOR_SPEED);
  M4.setSpeed(MOTOR_SPEED);
  Stop();
  Serial.println("BT Ready - Send F B L R S");
}

void loop() {
  if (Serial.available() > 0) {
    value = Serial.read();
    Serial.println(value);
  }
  if (value == 'F')      forward();
  else if (value == 'B') backward();
  else if (value == 'L') left();
  else if (value == 'R') right();
  else if (value == 'S') Stop();
}

void forward() {
  M1.run(FORWARD); M2.run(FORWARD);
  M3.run(FORWARD); M4.run(FORWARD);
}
void backward() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}
void left() {
  M1.run(FORWARD);  M2.run(FORWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}
void right() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(FORWARD);  M4.run(FORWARD);
}
void Stop() {
  M1.run(RELEASE); M2.run(RELEASE);
  M3.run(RELEASE); M4.run(RELEASE);
}
