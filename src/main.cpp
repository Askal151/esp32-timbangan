#include "Arduino.h"
#include "Preferences.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

// ── I2C (SDA=21, SCL=22 default ESP32) ─────
// ADS1015 address: ADDR→GND=0x48, VDD=0x49, SDA=0x4A, SCL=0x4B
#define ADS_ADDR    0x48

// Channel ADS1015 untuk sensor SS49E/OH49E
#define HALL_CH     0   // A0

// ── 4x LED bar ──────────────────────────────
#define LED1_PIN    32
#define LED2_PIN    33
#define LED3_PIN    18
#define LED4_PIN    19

const uint8_t LED_PINS[4] = {LED1_PIN, LED2_PIN, LED3_PIN, LED4_PIN};

// ── NVS (simpan threshold permanen) ─────────
Preferences prefs;

// ── ADS1015 ─────────────────────────────────
Adafruit_ADS1015 ads;

// ── Variabel global ──────────────────────────
int baseline     = 2048;
int thresh[4]    = {82, 329, 720, 1049};
int adc_val      = 0;
int deviation    = 0;
int led_count    = 0;

#define NOISE_FLOOR    15
#define MIN_THRESH_GAP 40
#define HYSTERESIS     8
#define DEBOUNCE_COUNT 5

// ── Baca ADS1015 (average) ───────────────────
int read_adc_avg(int samples = 32) {
    long sum = 0;
    for (int i = 0; i < samples; i++) {
        sum += ads.readADC_SingleEnded(HALL_CH);
        delay(2);
    }
    return (int)(sum / samples);
}

// Moving average buffer
#define MA_SIZE 32
int ma_buf[MA_SIZE] = {0};
int ma_idx = 0;
bool ma_full = false;

int read_adc_smooth() {
    ma_buf[ma_idx] = ads.readADC_SingleEnded(HALL_CH);
    ma_idx = (ma_idx + 1) % MA_SIZE;
    if (ma_idx == 0) ma_full = true;
    int count = ma_full ? MA_SIZE : ma_idx;
    long sum = 0;
    for (int i = 0; i < count; i++) sum += ma_buf[i];
    return (int)(sum / count);
}

void set_leds(int count) {
    for (int i = 0; i < 4; i++)
        digitalWrite(LED_PINS[i], i < count ? HIGH : LOW);
}

void save_thresholds() {
    prefs.begin("hall", false);
    prefs.putInt("t0", thresh[0]);
    prefs.putInt("t1", thresh[1]);
    prefs.putInt("t2", thresh[2]);
    prefs.putInt("t3", thresh[3]);
    prefs.putInt("base", baseline);
    prefs.end();
}

void load_thresholds() {
    prefs.begin("hall", true);
    thresh[0] = prefs.getInt("t0",  82);
    thresh[1] = prefs.getInt("t1", 329);
    thresh[2] = prefs.getInt("t2", 720);
    thresh[3] = prefs.getInt("t3", 1049);
    baseline  = prefs.getInt("base", 2048);
    prefs.end();
}

void calibrate_baseline() {
    Serial.println("[CAL] Jauhkan semua magnet...");
    delay(2000);
    baseline = read_adc_avg(128);
    Serial.print("[CAL] Baseline: ");
    Serial.println(baseline);
    save_thresholds();
}

void calibrate_magnet(int n) {
    if (n < 1 || n > 4) return;
    Serial.print("[CAL] Tempelkan ");
    Serial.print(n);
    Serial.println(" magnet ke sensor...");
    delay(2000);
    int val = read_adc_avg(128);
    int dev = abs(val - baseline);
    int new_thresh = (int)(dev * 0.75);

    if (dev < NOISE_FLOOR * 2) {
        Serial.println("[CAL] ERROR: Deviasi terlalu kecil!");
        return;
    }
    if (n > 1 && new_thresh <= thresh[n-2] + MIN_THRESH_GAP) {
        new_thresh = thresh[n-2] + MIN_THRESH_GAP;
        Serial.println("[CAL] Threshold disesuaikan agar bertahap.");
    }

    thresh[n-1] = new_thresh;
    Serial.print("[CAL] Magnet "); Serial.print(n);
    Serial.print(": ADC="); Serial.print(val);
    Serial.print(" Dev="); Serial.print(dev);
    Serial.print(" Threshold="); Serial.println(thresh[n-1]);
    save_thresholds();
    Serial.print("[THRESH] ");
    for (int i = 0; i < 4; i++) {
        Serial.print(thresh[i]);
        if (i < 3) Serial.print("|");
    }
    Serial.println();
}

void print_status() {
    Serial.println("=== STATUS ===");
    Serial.print("ADC IC   : ADS1015 @ 0x");
    Serial.println(ADS_ADDR, HEX);
    Serial.print("Channel  : A"); Serial.println(HALL_CH);
    Serial.print("Baseline : "); Serial.println(baseline);
    Serial.print("Threshold: ");
    for (int i = 0; i < 4; i++) {
        Serial.print("L"); Serial.print(i+1);
        Serial.print("="); Serial.print(thresh[i]);
        if (i < 3) Serial.print(" | ");
    }
    Serial.println();
    Serial.print("ADC      : "); Serial.println(adc_val);
    Serial.print("Deviasi  : "); Serial.println(deviation);
    Serial.print("LED aktif: "); Serial.println(led_count);
    Serial.println("==============");
}

// ── Setup ────────────────────────────────────
void setup() {
    Serial.begin(115200);

    for (int i = 0; i < 4; i++) {
        pinMode(LED_PINS[i], OUTPUT);
        digitalWrite(LED_PINS[i], LOW);
    }

    // Init ADS1015
    Wire.begin();
    if (!ads.begin(ADS_ADDR)) {
        Serial.println("[ERROR] ADS1015 tidak dijumpai! Semak wiring I2C.");
        while (1) { delay(500); }
    }
    // GAIN_ONE: ±4.096V → 1 LSB = 2mV
    ads.setGain(GAIN_ONE);

    load_thresholds();

    Serial.println("=== ESP32 + ADS1015 I2C → SS49E → LED Bar ===");
    Serial.println("I2C  : SDA=21 | SCL=22");
    Serial.print("ADS  : addr=0x"); Serial.print(ADS_ADDR, HEX);
    Serial.print(" | channel=A"); Serial.println(HALL_CH);
    Serial.println("LED  : GPIO 32, 33, 18, 19");
    Serial.println("Perintah:");
    Serial.println("  c  = kalibrasi baseline (tanpa magnet)");
    Serial.println("  1~4 = kalibrasi N magnet");
    Serial.println("  s  = status");
    Serial.println("  r  = reset threshold ke default");
    Serial.println("----------------------------------------------");
    Serial.print("[THRESH] ");
    for (int i = 0; i < 4; i++) {
        Serial.print(thresh[i]);
        if (i < 3) Serial.print("|");
    }
    Serial.println();
}

// ── Loop ─────────────────────────────────────
void loop() {
    if (Serial.available()) {
        char cmd = Serial.read();
        switch (cmd) {
            case 'c': case 'C': calibrate_baseline(); break;
            case '1': calibrate_magnet(1); break;
            case '2': calibrate_magnet(2); break;
            case '3': calibrate_magnet(3); break;
            case '4': calibrate_magnet(4); break;
            case 's': case 'S': print_status(); break;
            case 'r': case 'R':
                thresh[0]=82;  thresh[1]=329;
                thresh[2]=720; thresh[3]=1049;
                save_thresholds();
                Serial.println("[RESET] Threshold kembali ke default.");
                break;
            case 'T': {
                delay(50);
                String args = Serial.readStringUntil('\n');
                int t[4];
                int cnt = sscanf(args.c_str(), " %d %d %d %d",
                                 &t[0], &t[1], &t[2], &t[3]);
                if (cnt == 4 && t[0]>0 && t[1]>t[0] && t[2]>t[1] && t[3]>t[2]) {
                    for (int i = 0; i < 4; i++) thresh[i] = t[i];
                    save_thresholds();
                    Serial.print("[THRESH] ");
                    for (int i = 0; i < 4; i++) {
                        Serial.print(thresh[i]);
                        if (i < 3) Serial.print("|");
                    }
                    Serial.println();
                    Serial.println("[OK] Threshold dikemas kini.");
                } else {
                    Serial.println("[ERROR] Format: T t1 t2 t3 t4 (mesti menaik)");
                }
                break;
            }
        }
    }

    adc_val   = read_adc_smooth();
    deviation = abs(adc_val - baseline);
    int clean_dev = (deviation < NOISE_FLOOR) ? 0 : deviation;

    static int pending_count = 0;
    static int pending_ticks = 0;

    int raw_count = 0;
    for (int i = 0; i < 4; i++) {
        if (clean_dev >= thresh[i]) {
            raw_count = i + 1;
        } else if (clean_dev < thresh[i] - HYSTERESIS) {
            if (raw_count > i) raw_count = i;
        }
    }

    if (raw_count != led_count) {
        if (raw_count == pending_count) {
            pending_ticks++;
            if (pending_ticks >= DEBOUNCE_COUNT) {
                led_count = raw_count;
                pending_ticks = 0;
            }
        } else {
            pending_count = raw_count;
            pending_ticks = 1;
        }
    } else {
        pending_ticks = 0;
    }

    set_leds(led_count);

    // Output serial setiap 100ms — format sama dengan plotter.py
    static uint32_t last_print = 0;
    if (millis() - last_print >= 100) {
        last_print = millis();
        Serial.print("HALL|");
        Serial.print(adc_val);   Serial.print("|");
        Serial.print(deviation); Serial.print("|");
        Serial.println(led_count);
    }

    delay(5);
}
