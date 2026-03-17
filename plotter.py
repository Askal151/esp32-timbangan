import sys
import re
import serial
import serial.tools.list_ports
import threading
import csv
import os
from collections import deque
from datetime import datetime

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import numpy as np

# ── Konfigurasi ────────────────────────────
BAUD        = 115200
MAX_POINTS  = 300
REFRESH_MS  = 30
LOG_FILE    = os.path.join(os.path.dirname(__file__), 'data_log.csv')

# ── Auto detect port ───────────────────────
def find_port():
    for p in serial.tools.list_ports.comports():
        if any(c in p.description for c in ['CP210', 'CH340', 'CH341', 'FTDI']):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None

PORT = find_port()
if not PORT:
    print("[ERROR] ESP32 tidak dijumpai.")
    sys.exit(1)

print(f"[PORT] {PORT} | Baud: {BAUD} | Refresh: {1000//REFRESH_MS}fps")

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

# ── Data buffer ────────────────────────────
# Potensio
buf_pct    = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
buf_volt   = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
# Hall
buf_hall   = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
buf_count  = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)

cur_mode   = 'unknown'  # 'pot' atau 'hall'
cur_led    = 'OFF'
cur_pct    = 0.0
cur_volt   = 0.0
cur_raw    = 0
cur_hall   = 0
cur_count  = 0
cur_on_ms  = 0
lock       = threading.Lock()

pat_pot  = re.compile(r'(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|\s*([\d.]+)V\s*\|\s*(ON|OFF)')
pat_hall = re.compile(r'HALL\|([01])\|(\d+)\|(\d+)')

is_logging  = False
log_count   = 0
csv_writer  = None
csv_file_h  = None

# ── Serial thread ──────────────────────────
def serial_reader():
    global cur_mode, cur_led, cur_pct, cur_volt, cur_raw
    global cur_hall, cur_count, cur_on_ms, log_count, csv_writer
    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            ts   = datetime.now().strftime('%H:%M:%S.%f')[:-3]

            m_pot = pat_pot.search(line)
            m_hall = pat_hall.search(line)

            if m_pot:
                raw  = int(m_pot.group(1))
                pct  = float(m_pot.group(3))
                volt = float(m_pot.group(4))
                led  = m_pot.group(5)
                with lock:
                    cur_mode = 'pot'
                    buf_pct.append(pct)
                    buf_volt.append(volt)
                    cur_led = led; cur_pct = pct; cur_volt = volt; cur_raw = raw
                    if is_logging and csv_writer:
                        csv_writer.writerow([ts, raw, f'{pct:.1f}', f'{volt:.2f}', led])
                        log_count += 1

            elif m_hall:
                state = int(m_hall.group(1))
                cnt   = int(m_hall.group(2))
                onms  = int(m_hall.group(3))
                with lock:
                    cur_mode  = 'hall'
                    buf_hall.append(float(state))
                    buf_count.append(float(cnt))
                    cur_hall  = state
                    cur_count = cnt
                    cur_on_ms = onms
                    cur_led   = 'ON' if state else 'OFF'
                    if is_logging and csv_writer:
                        csv_writer.writerow([ts, state, cnt, onms])
                        log_count += 1
        except Exception:
            pass

t = threading.Thread(target=serial_reader, daemon=True)
t.start()

# ── PyQtGraph setup ────────────────────────
pg.setConfigOption('background', '#1a1a2e')
pg.setConfigOption('foreground', '#e0e0e0')

app = QtWidgets.QApplication(sys.argv)
win = QtWidgets.QWidget()
win.setWindowTitle('ESP32 Real-Time Plotter')
win.resize(1200, 750)
win.setStyleSheet("background:#1a1a2e; color:#e0e0e0;")

main_layout = QtWidgets.QHBoxLayout(win)
main_layout.setContentsMargins(8, 8, 8, 8)
main_layout.setSpacing(8)

# ── Graf ───────────────────────────────────
plot_widget = pg.GraphicsLayoutWidget()
main_layout.addWidget(plot_widget, stretch=3)

# Panel 1
p1 = plot_widget.addPlot(row=0, col=0)
p1.showGrid(x=True, y=True, alpha=0.3)
p1.setXRange(0, MAX_POINTS)
curve1 = p1.plot(pen=pg.mkPen('#00d4ff', width=2))
fill1  = pg.FillBetweenItem(curve1,
    p1.plot([0, MAX_POINTS], [0, 0], pen=None), brush=pg.mkBrush('#00d4ff18'))
p1.addItem(fill1)
thresh1 = pg.InfiniteLine(pos=50, angle=0,
    pen=pg.mkPen('#ff6b6b', width=1, style=QtCore.Qt.DashLine))
p1.addItem(thresh1)

# Panel 2
plot_widget.nextRow()
p2 = plot_widget.addPlot(row=1, col=0)
p2.showGrid(x=True, y=True, alpha=0.3)
p2.setXRange(0, MAX_POINTS)
p2.setLabel('bottom', 'Sampel')
curve2 = p2.plot(pen=pg.mkPen('#ff9f43', width=2))
fill2  = pg.FillBetweenItem(curve2,
    p2.plot([0, MAX_POINTS], [0, 0], pen=None), brush=pg.mkBrush('#ff9f4318'))
p2.addItem(fill2)

x = np.arange(MAX_POINTS)

# ── Panel kanan ────────────────────────────
right = QtWidgets.QVBoxLayout()
main_layout.addLayout(right, stretch=1)

def mlbl(text, size=10, color='#e0e0e0', bold=False):
    l = QtWidgets.QLabel(text)
    l.setStyleSheet(f"font-size:{size}pt; color:{color}; font-weight:{'bold' if bold else 'normal'};")
    l.setAlignment(QtCore.Qt.AlignCenter)
    l.setWordWrap(True)
    return l

def msep():
    f = QtWidgets.QFrame(); f.setFrameShape(QtWidgets.QFrame.HLine)
    f.setStyleSheet("color:#333;"); return f

def bstyle(c):
    return (f"QPushButton{{background:{c};color:white;border:none;padding:6px;"
            f"border-radius:4px;font-weight:bold;font-size:10pt;}}"
            f"QPushButton:hover{{background:{c}bb;}}"
            f"QPushButton:disabled{{background:#333;color:#666;}}")

lbl_mode   = mlbl('AUTO DETECT...', 11, '#888', bold=True)
lbl_val1   = mlbl('—', 22, '#00d4ff', bold=True)
lbl_val2   = mlbl('—', 16, '#ff9f43', bold=True)
lbl_val3   = mlbl('—', 10, '#aaa')
lbl_led    = mlbl('—', 14, '#e0e0e0', bold=True)

for w in [lbl_mode, lbl_val1, lbl_val2, lbl_val3, lbl_led]: right.addWidget(w)
right.addWidget(msep())

# Log controls
right.addWidget(mlbl('DATA LOGGING', 10, '#888', bold=True))
lbl_log_status = mlbl('● Idle', 10, '#888')
lbl_log_count  = mlbl('0 rekod', 10, '#aaa')
for w in [lbl_log_status, lbl_log_count]: right.addWidget(w)

btn_start = QtWidgets.QPushButton('⏺  Mula Log')
btn_stop  = QtWidgets.QPushButton('⏹  Stop Log')
btn_clear = QtWidgets.QPushButton('🗑  Kosong')
btn_open  = QtWidgets.QPushButton('📂  Buka CSV')
btn_start.setStyleSheet(bstyle('#2ecc71'))
btn_stop.setStyleSheet(bstyle('#e74c3c'))
btn_clear.setStyleSheet(bstyle('#e67e22'))
btn_open.setStyleSheet(bstyle('#3498db'))
btn_stop.setEnabled(False)
for w in [btn_start, btn_stop, btn_clear, btn_open]: right.addWidget(w)

right.addWidget(msep())
right.addWidget(mlbl('REKOD TERKINI', 10, '#888', bold=True))
table = QtWidgets.QTableWidget(0, 4)
table.setStyleSheet("background:#16213e; color:#e0e0e0; font-size:8pt; gridline-color:#333;")
table.horizontalHeader().setStyleSheet("background:#16213e; color:#aaa; font-size:8pt;")
table.verticalHeader().setVisible(False)
table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
table.setMaximumHeight(200)
right.addWidget(table)
right.addStretch()

table_rows = deque(maxlen=8)
last_count_logged = -1

# ── Log actions ────────────────────────────
def start_logging():
    global is_logging, csv_writer, csv_file_h, log_count
    if is_logging: return
    csv_file_h = open(LOG_FILE, 'a', newline='')
    csv_writer  = csv.writer(csv_file_h)
    mode = cur_mode
    if os.path.getsize(LOG_FILE) == 0:
        if mode == 'hall':
            csv_writer.writerow(['Masa', 'State', 'Kiraan', 'ON_ms'])
        else:
            csv_writer.writerow(['Masa', 'RAW', 'Peratus(%)', 'Voltan(V)', 'LED'])
    is_logging = True
    btn_start.setEnabled(False); btn_stop.setEnabled(True)
    lbl_log_status.setText('● Merakam...')
    lbl_log_status.setStyleSheet("font-size:10pt; color:#2ecc71; font-weight:bold;")

def stop_logging():
    global is_logging, csv_writer, csv_file_h
    if not is_logging: return
    is_logging = False
    if csv_file_h: csv_file_h.close()
    csv_writer = None
    btn_start.setEnabled(True); btn_stop.setEnabled(False)
    lbl_log_status.setText('● Berhenti')
    lbl_log_status.setStyleSheet("font-size:10pt; color:#e74c3c;")

def clear_log():
    global log_count
    stop_logging()
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    log_count = 0; table.setRowCount(0); table_rows.clear()
    lbl_log_count.setText('0 rekod')
    lbl_log_status.setText('● Idle')
    lbl_log_status.setStyleSheet("font-size:10pt; color:#888;")

def open_csv():
    if os.path.exists(LOG_FILE): os.startfile(LOG_FILE)

btn_start.clicked.connect(start_logging)
btn_stop.clicked.connect(stop_logging)
btn_clear.clicked.connect(clear_log)
btn_open.clicked.connect(open_csv)

# ── Update loop ────────────────────────────
def update():
    global last_count_logged
    with lock:
        mode   = cur_mode
        led    = cur_led
        pct    = cur_pct; volt = cur_volt; raw = cur_raw
        hall   = cur_hall; cnt = cur_count; onms = cur_on_ms
        p_data = np.array(buf_pct); v_data = np.array(buf_volt)
        h_data = np.array(buf_hall); c_data = np.array(buf_count)
        count  = log_count

    if mode == 'pot':
        p1.setTitle("<b>Peratus (%)</b>"); p1.setYRange(0, 105)
        p2.setTitle("<b>Voltan (V)</b>"); p2.setYRange(0, 3.5)
        thresh1.setPos(50); thresh1.setVisible(True)
        curve1.setData(x, p_data); curve2.setData(x, v_data)
        lbl_mode.setText('POTENSIO'); lbl_mode.setStyleSheet("font-size:11pt; color:#00d4ff; font-weight:bold;")
        lbl_val1.setText(f'{pct:.1f}%')
        lbl_val2.setText(f'{volt:.2f} V')
        lbl_val3.setText(f'RAW: {raw}')
        led_c = '#2ecc71' if led == 'ON' else '#e74c3c'
        lbl_led.setText(f'LED {led}')
        lbl_led.setStyleSheet(f"font-size:14pt; font-weight:bold; color:{led_c};")

        if is_logging and raw != last_count_logged:
            last_count_logged = raw
            ts = datetime.now().strftime('%H:%M:%S')
            row = [ts, str(raw), f'{pct:.1f}%', led]
            _add_table_row(row, ['Masa','RAW','%','LED'])
            lbl_log_count.setText(f'{count} rekod')

    elif mode == 'hall':
        p1.setTitle("<b>Hall State (1=Magnet / 0=Tiada)</b>"); p1.setYRange(-0.2, 1.5)
        p2.setTitle("<b>Kiraan Deteksi</b>"); p2.setYRange(0, max(float(cnt)+2, 5))
        thresh1.setVisible(False)
        curve1.setData(x, h_data); curve2.setData(x, c_data)
        lbl_mode.setText('HALL KY-003'); lbl_mode.setStyleSheet("font-size:11pt; color:#9b59b6; font-weight:bold;")
        state_txt = 'MAGNET' if hall else 'TIADA'
        state_c   = '#2ecc71' if hall else '#e74c3c'
        lbl_val1.setText(state_txt); lbl_val1.setStyleSheet(f"font-size:20pt; font-weight:bold; color:{state_c};")
        lbl_val2.setText(f'Kiraan: {cnt}')
        lbl_val2.setStyleSheet("font-size:14pt; font-weight:bold; color:#ff9f43;")
        lbl_val3.setText(f'Jumlah ON: {onms} ms')
        lbl_led.setText(f'LED {"ON" if hall else "OFF"}')
        lbl_led.setStyleSheet(f"font-size:14pt; font-weight:bold; color:{state_c};")

        if is_logging and cnt != last_count_logged:
            last_count_logged = cnt
            ts = datetime.now().strftime('%H:%M:%S')
            row = [ts, state_txt, str(cnt), f'{onms}ms']
            _add_table_row(row, ['Masa','State','Kiraan','ON ms'])
            lbl_log_count.setText(f'{count} rekod')

def _add_table_row(row_data, headers):
    if table.columnCount() != len(headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        for i in range(len(headers)-1): table.setColumnWidth(i, 70)
        table.horizontalHeader().setStretchLastSection(True)
    table_rows.append(row_data)
    table.setRowCount(0)
    for r in reversed(table_rows):
        pos = table.rowCount(); table.insertRow(pos)
        for col, val in enumerate(r):
            item = QtWidgets.QTableWidgetItem(val)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(pos, col, item)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(REFRESH_MS)

win.show()
print(f"[PLOTTER] Auto-detect sensor | ~{1000//REFRESH_MS}fps")

try:
    app.exec_()
finally:
    stop_logging()
    ser.close()
    print("[PLOTTER] Selesai.")
