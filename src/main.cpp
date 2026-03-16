#include "HX711.h"

// Pin HX711
#define DOUT_PIN  4
#define SCK_PIN   5

HX711 scale;

// Faktor kalibrasi - ubah nilai ini saat kalibrasi
// Nilai positif atau negatif bergantung pada orientasi load cell
float calibration_factor = -7050.0;

void setup() {
  Serial.begin(115200);
  Serial.println("=== ESP32 Timbangan Digital ===");
  Serial.println("Inisialisasi HX711...");

  scale.begin(DOUT_PIN, SCK_PIN);

  if (!scale.is_ready()) {
    Serial.println("ERROR: HX711 tidak terdeteksi! Periksa koneksi.");
    while (1) delay(500);
  }

  Serial.println("HX711 siap.");
  Serial.println("Mengatur tara (kosongkan timbangan)...");
  delay(2000);

  scale.set_scale(calibration_factor);
  scale.tare(); // Reset ke 0 dengan kondisi kosong

  Serial.println("Tara selesai. Timbangan siap digunakan.");
  Serial.println("-------------------------------------");
  Serial.println("Perintah Serial:");
  Serial.println("  't' = Tara ulang (reset ke 0)");
  Serial.println("  '+' = Naikkan calibration_factor sebesar 10");
  Serial.println("  '-' = Turunkan calibration_factor sebesar 10");
  Serial.println("-------------------------------------");
}

void loop() {
  // Baca perintah dari Serial Monitor
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 't' || cmd == 'T') {
      scale.tare();
      Serial.println("[TARA] Berat direset ke 0.");
    } else if (cmd == '+') {
      calibration_factor += 10;
      scale.set_scale(calibration_factor);
      Serial.print("[KALIBRASI] Factor: ");
      Serial.println(calibration_factor);
    } else if (cmd == '-') {
      calibration_factor -= 10;
      scale.set_scale(calibration_factor);
      Serial.print("[KALIBRASI] Factor: ");
      Serial.println(calibration_factor);
    }
  }

  // Baca berat (rata-rata 10 pembacaan untuk stabilitas)
  if (scale.is_ready()) {
    float berat_gram = scale.get_units(10);
    float berat_kg   = berat_gram / 1000.0;

    Serial.print("Berat: ");
    Serial.print(berat_gram, 1); // 1 desimal
    Serial.print(" g  |  ");
    Serial.print(berat_kg, 3);   // 3 desimal
    Serial.println(" kg");
  } else {
    Serial.println("HX711 tidak siap, mencoba ulang...");
  }

  delay(500); // Baca setiap 0.5 detik
}
