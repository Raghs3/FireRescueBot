# Sensor Wiring Guide

## Pin Assignment Summary

| Sensor | Arduino Pin |
|---|---|
| Flame sensor (AO) | A4 |
| MQ-2 gas sensor (AO) | A2 |
| DHT11 data | 7 |
| Ultrasonic TRIG | A1 |
| Ultrasonic ECHO | A0 |
| Buzzer (+) | 2 |

---

## 1. Flame Sensor

**Pins:** VCC, GND, DO (digital out), AO (analog out)  
**Use:** AO pin only — gives analog value, better sensitivity than DO.

| Sensor Pin | Connect to |
|---|---|
| VCC | 5V |
| GND | GND |
| AO | A4 |
| DO | not connected |

**How it works:** Lower analog value = more flame. Threshold set at 500 (0–1023 scale).  
**Demo trigger:** Hold lighter ~5–10cm from sensor face.

---

## 2. MQ-2 Gas / Smoke Sensor

**Pins:** VCC, GND, DO, AO  
**Use:** AO pin — analog reading for gas concentration.

| Sensor Pin | Connect to |
|---|---|
| VCC | 5V |
| GND | GND |
| AO | A2 |
| DO | not connected |

**Note:** MQ-2 needs ~2 min warm-up after power on for accurate readings.  
**How it works:** Higher analog value = more gas. Threshold set at 400.  
**Demo trigger:** Hold lighter gas (unlit) near sensor, or blow smoke near it.

---

## 3. DHT11 Temperature & Humidity Sensor

**Pins:** + (VCC), out (DATA), - (GND)  
**Requires:** 10KΩ pull-up resistor between DATA and VCC.

| Sensor Pin | Connect to |
|---|---|
| + (VCC) | 5V |
| out (DATA) | Pin 7 + 10KΩ resistor to 5V |
| - (GND) | GND |

```
5V ──┬── 10KΩ ──┬── Pin 7
     │           │
    VCC         DATA
               DHT11
               GND ── GND
```

**How it works:** Reads temperature (°C) and humidity (%). Alert fires above 45°C.  
**Demo trigger:** Pinch DHT11 between fingers to warm it up slowly.  
**Library:** Install `DHT sensor library` by Adafruit in Arduino Library Manager.

---

## 4. HC-SR04 Ultrasonic Sensor

**Pins:** VCC, TRIG, ECHO, GND

| Sensor Pin | Connect to |
|---|---|
| VCC | 5V |
| TRIG | A1 |
| ECHO | A0 |
| GND | GND |

**How it works:** Measures distance in cm. Car stops forward movement when obstacle within 12cm.  
**Demo trigger:** Move hand toward sensor while car is driving forward.

---

## 5. Buzzer

**Pins:** + (longer leg), - (shorter leg)

| Buzzer Pin | Connect to |
|---|---|
| + (longer leg) | Pin 2 |
| - (shorter leg) | GND |

**No resistor needed.**

---

## Alert Behavior Summary

| Condition | Threshold | Buzzer Pattern | Action |
|---|---|---|---|
| Gas detected | MQ-2 analog > 400 | Continuous 1000Hz tone | ALERT: GAS |
| Flame detected | Flame analog < 500 | 3 rapid beeps | ALERT: FLAME |
| High temperature | Temp > 45°C | 2 slow beeps | ALERT: HIGH TEMP |
| Obstacle | Distance < 12cm | 1 short beep | Block forward |
| All clear | — | Silent | Normal operation |

Priority order: **Gas > Flame > High Temp > Obstacle**

---

## Power Notes

- All sensors run on **5V** from Arduino
- MQ-2 draws ~150mA — if Arduino resets randomly, power MQ-2 from separate 5V supply
- Motor shield has its own power terminal — use 6–12V battery for motors, separate from Arduino 5V

---

## Libraries Required (Arduino IDE)

Install via **Sketch → Include Library → Manage Libraries**:

| Library | Install name |
|---|---|
| DHT11/22 | `DHT sensor library` by Adafruit |
| AFMotor (motors) | `Adafruit Motor Shield library` |
