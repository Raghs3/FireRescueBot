#include <AFMotor.h>
#include <DHT.h>

// --- Pin assignments ---
#define MQ2_PIN      A2
#define DHT_PIN      7
#define ECHO_PIN     A0
#define TRIG_PIN     A1
#define BUZZER_PIN   2

// --- Thresholds ---
#define DHT_TYPE        DHT11
#define MOTOR_SPEED     170
#define SAFE_DIST_CM    12
#define GAS_THRESHOLD   150    // analog > this = gas (ambient 30-70, lighter gas hits 200+)
#define HIGH_TEMP_C     45.0
#define SENSOR_MS       800

#define ALERT_NONE     0
#define ALERT_OBSTACLE 1
#define ALERT_HIGHTEMP 2
#define ALERT_GAS      3

AF_DCMotor M1(1);
AF_DCMotor M2(2);
AF_DCMotor M3(3);
AF_DCMotor M4(4);
DHT dht(DHT_PIN, DHT_TYPE);

char cmd = 'S';
unsigned long lastSensorMs = 0;

// -------------------------------------------------------
void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  dht.begin();
  M1.setSpeed(MOTOR_SPEED); M2.setSpeed(MOTOR_SPEED);
  M3.setSpeed(MOTOR_SPEED); M4.setSpeed(MOTOR_SPEED);
  motorStop();

  Serial.println("=== STARTUP DIAGNOSTICS ===");
  delay(2000);

  float t = dht.readTemperature(), h = dht.readHumidity();
  if (isnan(t)) Serial.println("[DHT11]      FAIL - check pin 7");
  else { Serial.print("[DHT11]      OK  Temp="); Serial.print(t); Serial.print("C  Hum="); Serial.print(h); Serial.println("%"); }

  int g = analogRead(MQ2_PIN);
  Serial.print("[MQ-2]       OK  Raw="); Serial.print(g);
  Serial.println(g > GAS_THRESHOLD ? "  ** GAS **" : "  no gas");

  int d = getDistance();
  if (d == -1) Serial.println("[ULTRASONIC] FAIL - check A0/A1");
  else { Serial.print("[ULTRASONIC] OK  Dist="); Serial.print(d); Serial.println("cm"); }

  Serial.println("[BUZZER]     Testing...");
  beepShort(); delay(300); beepShort();

  Serial.println("=== READY — Send F/B/L/R/S via Bluetooth ===");
  Serial.println("=== Live: S:gas,temp,hum,dist,alert ===");
}

// -------------------------------------------------------
void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'F' || c == 'B' || c == 'L' || c == 'R' || c == 'S') {
      cmd = c;
    }
  }

  int gas  = (analogRead(MQ2_PIN) > GAS_THRESHOLD);
  int dist = getDistance();
  bool obstacle = (dist > 0 && dist <= SAFE_DIST_CM && cmd == 'F');

  int alert = ALERT_NONE;
  if (obstacle) alert = ALERT_OBSTACLE;
  if (gas)      alert = ALERT_GAS;

  if (alert == ALERT_GAS) {
    motorStop(); cmd = 'S';
  } else if (obstacle) {
    motorStop();
  } else {
    runMotors(cmd);
  }

  switch (alert) {
    case ALERT_GAS:      tone(BUZZER_PIN, 1000);              break;
    case ALERT_OBSTACLE: beepShort();                         break;
    default:             noTone(BUZZER_PIN);                  break;
  }

  if (millis() - lastSensorMs >= SENSOR_MS) {
    reportSensors(gas, dist, alert);
    lastSensorMs = millis();
  }
}

// -------------------------------------------------------
void reportSensors(int gas, int dist, int alert) {
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  int gasRaw = analogRead(MQ2_PIN);

  if (!isnan(temp) && temp >= HIGH_TEMP_C && alert == ALERT_NONE) {
    alert = ALERT_HIGHTEMP;
    motorStop(); cmd = 'S';
    beepBurst(2, 300, 300);
  }

  Serial.print("RAW  gas="); Serial.print(gasRaw);
  Serial.print("  dist="); Serial.print(dist); Serial.println("cm");

  Serial.print("S:");
  Serial.print(gas); Serial.print(",");
  isnan(temp) ? Serial.print(-1) : Serial.print(temp, 1);
  Serial.print(",");
  isnan(hum)  ? Serial.print(-1) : Serial.print(hum, 1);
  Serial.print(",");
  Serial.print(dist); Serial.print(",");
  Serial.println(alert);

  Serial.print("  >> ");
  switch (alert) {
    case ALERT_GAS:      Serial.println("ALERT: GAS/SMOKE — car stopped"); break;
    case ALERT_HIGHTEMP: Serial.print("ALERT: HIGH TEMP "); Serial.print(temp); Serial.println("C — car stopped"); break;
    case ALERT_OBSTACLE: Serial.println("ALERT: OBSTACLE — forward blocked"); break;
    default:             Serial.println("OK"); break;
  }
}

// -------------------------------------------------------
int getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long t = pulseIn(ECHO_PIN, HIGH, 38000);
  delay(60);  // wait before next ping
  return (t == 0) ? -1 : (int)(t / 58);
}

void beepShort() { tone(BUZZER_PIN, 1000, 100); delay(150); }

void beepBurst(int n, int onMs, int offMs) {
  for (int i = 0; i < n; i++) {
    tone(BUZZER_PIN, 1200, onMs);
    delay(onMs + offMs);
  }
}

void runMotors(char c) {
  switch (c) {
    case 'F': motorForward();  break;
    case 'B': motorBackward(); break;
    case 'L': motorLeft();     break;
    case 'R': motorRight();    break;
    default:  motorStop();     break;
  }
}

void motorForward()  { M1.run(FORWARD);  M2.run(FORWARD);  M3.run(FORWARD);  M4.run(FORWARD);  }
void motorBackward() { M1.run(BACKWARD); M2.run(BACKWARD); M3.run(BACKWARD); M4.run(BACKWARD); }
void motorLeft()     { M1.run(FORWARD);  M2.run(FORWARD);  M3.run(BACKWARD); M4.run(BACKWARD); }
void motorRight()    { M1.run(BACKWARD); M2.run(BACKWARD); M3.run(FORWARD);  M4.run(FORWARD);  }
void motorStop()     { M1.run(RELEASE);  M2.run(RELEASE);  M3.run(RELEASE);  M4.run(RELEASE);  }
