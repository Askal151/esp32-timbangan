#include "Arduino.h"

// ── Pin Sensor Hall (4x KY-003) ────────────
#define HALL1_PIN  14
#define HALL2_PIN  27
#define HALL3_PIN  26
#define HALL4_PIN  13

// ── Pin LED External ───────────────────────
#define LED1_PIN   32
#define LED2_PIN   33
#define LED3_PIN   18
#define LED4_PIN   19

// ── LED internal ───────────────────────────
#define LED_INT     2    // ON bila mana-mana magnet aktif

// ── DAC output ─────────────────────────────
#define DAC_PIN    25    // voltan ikut bilangan magnet aktif

// ── Konfigurasi ────────────────────────────
#define DEBOUNCE_MS  30
#define ACTIVE_LOW   true   // KY-003: LOW = magnet terdeteksi

// ── Struct sensor ──────────────────────────
struct HallSensor {
  uint8_t  hall_pin;
  uint8_t  led_pin;
  bool     state;        // state stabil semasa
  bool     raw_prev;     // bacaan sebelum debounce
  uint32_t last_change;  // masa berubah terakhir
};

HallSensor sensors[] = {
  {HALL1_PIN, LED1_PIN, false, false, 0},
  {HALL2_PIN, LED2_PIN, false, false, 0},
  {HALL3_PIN, LED3_PIN, false, false, 0},
  {HALL4_PIN, LED4_PIN, false, false, 0},
};
const int NUM_SENSORS = 4;

// Voltan output DAC ikut bilangan magnet aktif
const float dac_volt[] = {0.00, 0.83, 1.65, 2.48, 3.30};
const uint8_t dac_val[] = {0,   64,   128,  192,  255};

void update_dac_led(int active_count) {
  dacWrite(DAC_PIN, dac_val[active_count]);
  digitalWrite(LED_INT, active_count > 0 ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_INT, OUTPUT);
  digitalWrite(LED_INT, LOW);
  dacWrite(DAC_PIN, 0);

  for (int i = 0; i < NUM_SENSORS; i++) {
    pinMode(sensors[i].hall_pin, INPUT_PULLUP);
    pinMode(sensors[i].led_pin,  OUTPUT);
    digitalWrite(sensors[i].led_pin, LOW);
  }

  Serial.println("=== ESP32 Hall Sensor x4 Real-Time ===");
  Serial.println("Sensor | GPIO Hall | GPIO LED");
  Serial.println("   1   |   14     |   32");
  Serial.println("   2   |   27     |   33");
  Serial.println("   3   |   26     |   18");
  Serial.println("   4   |   13     |   19");
  Serial.println("DAC Output: GPIO 25");
  Serial.println("--------------------------------------");
  Serial.println("Perintah: 's' = status");
  Serial.println("--------------------------------------");
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 's' || cmd == 'S') {
      Serial.println("=== STATUS ===");
      int cnt = 0;
      for (int i = 0; i < NUM_SENSORS; i++) {
        Serial.print("  Sensor "); Serial.print(i+1);
        Serial.print(": "); Serial.println(sensors[i].state ? "MAGNET ON" : "tiada");
        if (sensors[i].state) cnt++;
      }
      Serial.print("  Aktif: "); Serial.print(cnt);
      Serial.print(" | DAC: "); Serial.print(dac_volt[cnt]);
      Serial.println("V");
      Serial.println("==============");
    }
  }

  int active_count = 0;
  bool changed     = false;

  for (int i = 0; i < NUM_SENSORS; i++) {
    bool raw      = digitalRead(sensors[i].hall_pin);
    bool detected = ACTIVE_LOW ? (raw == LOW) : (raw == HIGH);

    // Debounce
    if (detected != sensors[i].raw_prev) {
      sensors[i].last_change = millis();
      sensors[i].raw_prev    = detected;
    }

    if ((millis() - sensors[i].last_change) >= DEBOUNCE_MS) {
      if (detected != sensors[i].state) {
        sensors[i].state = detected;
        changed = true;

        Serial.print("[S"); Serial.print(i+1); Serial.print("] ");
        Serial.println(detected ? "MAGNET ON" : "OFF");
      }
    }

    if (sensors[i].state) active_count++;
    digitalWrite(sensors[i].led_pin, sensors[i].state ? HIGH : LOW);
  }

  if (changed) {
    update_dac_led(active_count);
    Serial.print(">> Aktif: "); Serial.print(active_count);
    Serial.print(" | DAC: "); Serial.print(dac_volt[active_count]);
    Serial.println("V");
  }

  // Output untuk plotter
  static uint32_t last_plot = 0;
  if (millis() - last_plot >= 100) {
    last_plot = millis();
    Serial.print("HALL|");
    Serial.print(sensors[0].state ? 1 : 0); Serial.print("|");
    Serial.print(sensors[1].state ? 1 : 0); Serial.print("|");
    Serial.print(sensors[2].state ? 1 : 0); Serial.print("|");
    Serial.print(sensors[3].state ? 1 : 0); Serial.print("|");
    Serial.println(active_count);
  }

  delay(5);
}
