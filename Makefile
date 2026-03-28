PIO    := $(shell which pio 2>/dev/null || echo /home/manticore/.platformio/penv/bin/pio)
PYTHON := $(shell test -f /home/manticore/.platformio/penv/bin/python3 && echo /home/manticore/.platformio/penv/bin/python3 || echo python3)

# Auto detect ESP32 port (CP210x, CH340, CH341, FTDI) - utamakan ttyUSB/ttyACM
ESP_PORT := $(shell $(PIO) device list 2>/dev/null | grep -B5 -E 'CP210|CH340|CH341|FTDI' | grep -E '^/dev/tty(USB|ACM)' | head -1)
ifeq ($(ESP_PORT),)
	ESP_PORT := $(shell $(PIO) device list 2>/dev/null | grep -E '^/dev/tty(USB|ACM)' | head -1)
endif

.PHONY: help build upload monitor um clean ports libs plot analyze kill

help:
	@echo ""
	@echo " ╔══════════════════════════════════════╗"
	@echo " ║   ESP32 PlatformIO Build Tool        ║"
	@echo " ╚══════════════════════════════════════╝"
	@echo ""
	@echo "  build     - Compile sahaja"
	@echo "  upload    - Compile + upload ke ESP32"
	@echo "  monitor   - Buka Serial Monitor (115200)"
	@echo "  um        - Upload + terus buka monitor"
	@echo "  clean     - Padam hasil build"
	@echo "  ports     - Senarai port yang ada"
	@echo "  libs      - Pasang semula library"
	@echo "  plot      - Buka real-time graf potensio"
	@echo "  analyze   - Analisa dan replay data log CSV"
	@echo "  kill      - Kill semua proses yang pegang port"
	@echo ""
	@echo " Guna: make <arahan>"
	@echo ""

build:
	@echo ""
	@echo "[BUILD] Compiling..."
	$(PIO) run

upload: _check_port
	@echo ""
	@echo "[UPLOAD] Compiling dan upload ke $(ESP_PORT)..."
	$(PIO) run --target upload --upload-port $(ESP_PORT)

monitor: _check_port
	@echo ""
	@echo "[MONITOR] Serial Monitor pada $(ESP_PORT) - tekan Ctrl+C untuk keluar..."
	$(PIO) device monitor --port $(ESP_PORT) --baud 115200

um: _check_port
	@echo ""
	@echo "[UPLOAD + MONITOR] Upload ke $(ESP_PORT) kemudian buka monitor..."
	$(PIO) run --target upload --upload-port $(ESP_PORT) && \
	$(PIO) device monitor --port $(ESP_PORT) --baud 115200

clean:
	@echo ""
	@echo "[CLEAN] Membuang fail build..."
	$(PIO) run --target clean

ports:
	@echo ""
	@echo "[PORTS] Port yang tersedia:"
	$(PIO) device list

libs:
	@echo ""
	@echo "[LIBS] Memasang semula library..."
	$(PIO) lib install

plot:
	@echo ""
	@echo "[PLOT] Membuka real-time graf..."
	$(PYTHON) plotter.py

analyze:
	@echo ""
	@echo "[ANALYZE] Membuka analyzer..."
	$(PYTHON) analyzer.py

kill:
	@echo ""
	@echo "[KILL] Menutup semua proses yang mungkin pegang port..."
	-pkill -f "pio device monitor" && echo " - pio monitor ditutup" || echo " - pio monitor tiada"
	-pkill -f "miniterm" && echo " - miniterm ditutup" || echo " - miniterm tiada"
	-pkill -f "plotter.py" && echo " - plotter.py ditutup" || echo " - plotter.py tiada"
	@echo "[KILL] Selesai. Port kini bebas."

_check_port:
	@if [ -z "$(ESP_PORT)" ]; then \
		echo "[ERROR] Tiada port ESP32 dijumpai. Pastikan ESP32 disambung."; \
		exit 1; \
	fi
	@echo "[PORT] ESP32 dijumpai di: $(ESP_PORT)"
