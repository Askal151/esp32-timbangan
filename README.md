# ESP32 Timbangan Digital

Projek timbangan digital menggunakan ESP32 dan modul HX711 dengan load cell.

---

## Perkakasan (Hardware)

| Komponen | Pin ESP32 |
|----------|-----------|
| HX711 DOUT | GPIO 4 |
| HX711 SCK  | GPIO 5 |
| HX711 VCC  | 3.3V / 5V |
| HX711 GND  | GND |

---

## Keperluan

- [Python 3.x](https://www.python.org/downloads/)
- PlatformIO Core (sudah terpasang di `C:\Users\Dell\.platformio\`)

---

## Struktur Projek

```
esp32_timbangan/
├── src/
│   └── main.cpp          ← kod utama
├── platformio.ini        ← konfigurasi PlatformIO
├── pio.bat               ← skrip build/upload
└── README.md
```

---

## Setup Pertama Kali

**1. Sambung ESP32 ke komputer via USB**

**2. Semak port COM ESP32:**
```cmd
pio.bat ports
```

**3. (Jika perlu) Tetapkan port dalam `platformio.ini`:**
```ini
upload_port = COM3
```

---

## Cara Guna `pio.bat`

Double-click `pio.bat` untuk menu interaktif, atau jalankan terus dari terminal:

| Arahan | Fungsi |
|--------|--------|
| `pio.bat build` | Compile kod sahaja |
| `pio.bat upload` | Compile + upload ke ESP32 |
| `pio.bat monitor` | Buka Serial Monitor (115200 baud) |
| `pio.bat um` | Upload kemudian terus buka monitor |
| `pio.bat clean` | Padam fail hasil build |
| `pio.bat ports` | Senarai port COM yang ada |
| `pio.bat libs` | Pasang semula library |

---

## Kalibrasi Timbangan

Nilai kalibrasi semasa: `-7050.0`

Semasa Serial Monitor dibuka, hantar perintah:

| Perintah | Fungsi |
|----------|--------|
| `t` | Tara — reset berat ke 0 |
| `+` | Naikkan calibration_factor (+10) |
| `-` | Turunkan calibration_factor (-10) |

**Langkah kalibrasi:**
1. Kosongkan timbangan, hantar `t` untuk tara
2. Letak objek yang diketahui beratnya (contoh: 500g)
3. Laras `+` atau `-` sehingga bacaan tepat
4. Catat nilai `calibration_factor` yang betul dan kemaskini dalam `src/main.cpp`

---

## Library

- [bogde/HX711](https://github.com/bogde/HX711) `^0.7.5` — auto dipasang oleh PlatformIO
