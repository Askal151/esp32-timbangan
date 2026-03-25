"""
Test script untuk verifikasi PyQt5 + pyqtgraph berjalan dengan betul.
Mensimulasikan data sensor ESP32 tanpa perlu sambungan serial.
"""
import sys
import math
import random
from collections import deque

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# ── Konfigurasi ────────────────────────────
MAX_POINTS = 300
REFRESH_MS = 30
BAUD       = 115200

# ── Simulasi data sensor ────────────────────
t_step = 0
def sim_pot():
    """Simulasi data potensio: gelombang sinus + noise"""
    global t_step
    t_step += 1
    pct  = 50 + 40 * math.sin(t_step * 0.05) + random.uniform(-2, 2)
    volt = pct / 100 * 3.3
    led  = 'ON' if pct > 50 else 'OFF'
    return max(0, min(100, pct)), max(0, min(3.3, volt)), led

def sim_hall():
    """Simulasi data Hall sensor: togol setiap ~50 tick"""
    global t_step
    state = 1 if (t_step // 50) % 2 == 0 else 0
    return state

# ── Data buffer ─────────────────────────────
buf_pct  = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
buf_volt = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
x        = np.arange(MAX_POINTS)

# ── PyQtGraph setup ─────────────────────────
pg.setConfigOption('background', '#1a1a2e')
pg.setConfigOption('foreground', '#e0e0e0')

app = QtWidgets.QApplication(sys.argv)
win = QtWidgets.QWidget()
win.setWindowTitle('TEST - ESP32 PyQt Simulator')
win.resize(1100, 650)
win.setStyleSheet("background:#1a1a2e; color:#e0e0e0;")

main_layout = QtWidgets.QHBoxLayout(win)
main_layout.setContentsMargins(8, 8, 8, 8)
main_layout.setSpacing(8)

# ── Graf ────────────────────────────────────
plot_widget = pg.GraphicsLayoutWidget()
main_layout.addWidget(plot_widget, stretch=3)

p1 = plot_widget.addPlot(row=0, col=0, title="<b>Peratus (%) — SIMULASI</b>")
p1.showGrid(x=True, y=True, alpha=0.3)
p1.setYRange(0, 105)
p1.setXRange(0, MAX_POINTS)
curve1 = p1.plot(pen=pg.mkPen('#00d4ff', width=2))
thresh = pg.InfiniteLine(pos=50, angle=0,
    pen=pg.mkPen('#ff6b6b', width=1, style=QtCore.Qt.DashLine))
p1.addItem(thresh)

plot_widget.nextRow()
p2 = plot_widget.addPlot(row=1, col=0, title="<b>Voltan (V) — SIMULASI</b>")
p2.showGrid(x=True, y=True, alpha=0.3)
p2.setYRange(0, 3.5)
p2.setXRange(0, MAX_POINTS)
p2.setLabel('bottom', 'Sampel')
curve2 = p2.plot(pen=pg.mkPen('#ff9f43', width=2))

# ── Panel kanan ──────────────────────────────
right = QtWidgets.QVBoxLayout()
main_layout.addLayout(right, stretch=1)

def mlbl(text, size=10, color='#e0e0e0', bold=False):
    l = QtWidgets.QLabel(text)
    l.setStyleSheet(f"font-size:{size}pt; color:{color}; font-weight:{'bold' if bold else 'normal'};")
    l.setAlignment(QtCore.Qt.AlignCenter)
    return l

lbl_title  = mlbl('[ TEST MODE ]', 11, '#f39c12', bold=True)
lbl_status = mlbl('PyQt5 + pyqtgraph OK', 10, '#2ecc71', bold=True)
lbl_val1   = mlbl('0.0%', 24, '#00d4ff', bold=True)
lbl_val2   = mlbl('0.00 V', 16, '#ff9f43', bold=True)
lbl_led    = mlbl('LED OFF', 14, '#e74c3c', bold=True)

sep = QtWidgets.QFrame()
sep.setFrameShape(QtWidgets.QFrame.HLine)
sep.setStyleSheet("color:#333;")

lbl_info = mlbl('Simulasi data sensor\ntanpa ESP32', 9, '#888')

# Counter FPS
lbl_fps = mlbl('FPS: --', 9, '#555')

right.addWidget(lbl_title)
right.addWidget(lbl_status)
right.addWidget(sep)
right.addWidget(lbl_val1)
right.addWidget(lbl_val2)
right.addWidget(lbl_led)
right.addStretch()
right.addWidget(lbl_info)
right.addWidget(lbl_fps)

# ── FPS counter ──────────────────────────────
frame_count = 0
fps_timer_val = 0

def update():
    global frame_count, fps_timer_val

    pct, volt, led = sim_pot()
    buf_pct.append(pct)
    buf_volt.append(volt)

    curve1.setData(x, np.array(buf_pct))
    curve2.setData(x, np.array(buf_volt))

    lbl_val1.setText(f'{pct:.1f}%')
    lbl_val2.setText(f'{volt:.2f} V')

    led_color = '#2ecc71' if led == 'ON' else '#e74c3c'
    lbl_led.setText(f'LED {led}')
    lbl_led.setStyleSheet(f"font-size:14pt; font-weight:bold; color:{led_color};")

    frame_count += 1
    fps_timer_val += REFRESH_MS
    if fps_timer_val >= 1000:
        lbl_fps.setText(f'FPS: {frame_count}')
        frame_count = 0
        fps_timer_val = 0

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(REFRESH_MS)

win.show()
print("[TEST] PyQt5 + pyqtgraph berjalan dengan jayanya!")
print(f"[TEST] Refresh: ~{1000//REFRESH_MS}fps | MAX_POINTS: {MAX_POINTS}")
print("[TEST] Tutup tetingkap untuk keluar.")

sys.exit(app.exec_())
