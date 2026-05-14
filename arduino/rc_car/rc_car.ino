#include <AFMotor.h>

#define ECHO_PIN A0
#define TRIG_PIN A1
#define MOTOR_SPEED 170
#define SAFE_DISTANCE_CM 12

AF_DCMotor M1(1);
AF_DCMotor M2(2);
AF_DCMotor M3(3);
AF_DCMotor M4(4);

char cmd = 'S';

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  M1.setSpeed(MOTOR_SPEED);
  M2.setSpeed(MOTOR_SPEED);
  M3.setSpeed(MOTOR_SPEED);
  M4.setSpeed(MOTOR_SPEED);
  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    cmd = Serial.read();
  }

  if (getDistance() <= SAFE_DISTANCE_CM && cmd == 'F') {
    stopMotors();
    return;
  }

  switch (cmd) {
    case 'F': forward();     break;
    case 'B': backward();    break;
    case 'L': turnLeft();    break;
    case 'R': turnRight();   break;
    case 'S': stopMotors();  break;
  }
}

int getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(4);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long t = pulseIn(ECHO_PIN, HIGH);
  return (int)(t / 29 / 2);
}

void forward() {
  M1.run(FORWARD); M2.run(FORWARD);
  M3.run(FORWARD); M4.run(FORWARD);
}

void backward() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}

void turnLeft() {
  M1.run(FORWARD);  M2.run(FORWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}

void turnRight() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(FORWARD);  M4.run(FORWARD);
}

void stopMotors() {
  M1.run(RELEASE); M2.run(RELEASE);
  M3.run(RELEASE); M4.run(RELEASE);
}
