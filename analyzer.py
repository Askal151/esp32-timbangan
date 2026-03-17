import sys
import csv
import os
import time
import threading
from datetime import datetime
from collections import Counter

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import numpy as np

LOG_FILE = os.path.join(os.path.dirname(__file__), 'data_log.csv')

# ── Baca CSV ───────────────────────────────
def load_csv(path):
    rows = []
    try:
        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    rows.append({
                        'time': r['Masa'],
                        'raw':  int(r['RAW']),
                        'pct':  float(r['Peratus(%)']),
                        'volt': float(r['Voltan(V)']),
                        'led':  r['LED'].strip()
                    })
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return rows

# ── Analisa statistik ──────────────────────
def analyze(rows):
    if not rows:
        return {}
    pcts  = [r['pct']  for r in rows]
    volts = [r['volt'] for r in rows]
    leds  = [r['led']  for r in rows]
    on_count  = leds.count('ON')
    off_count = leds.count('OFF')
    total     = len(rows)

    # Durasi ON/OFF berturut
    max_on = max_off = cur = 0
    prev = None
    for l in leds:
        if l == prev: cur += 1
        else: cur = 1
        if l == 'ON'  and cur > max_on:  max_on  = cur
        if l == 'OFF' and cur > max_off: max_off = cur
        prev = l

    return {
        'total':    total,
        'pct_min':  min(pcts),
        'pct_max':  max(pcts),
        'pct_avg':  np.mean(pcts),
        'pct_std':  np.std(pcts),
        'volt_min': min(volts),
        'volt_max': max(volts),
        'volt_avg': np.mean(volts),
        'led_on_pct':  (on_count / total) * 100,
        'led_off_pct': (off_count / total) * 100,
        'led_on_count':  on_count,
        'led_off_count': off_count,
        'max_on_streak':  max_on,
        'max_off_streak': max_off,
    }

# ── UI ─────────────────────────────────────
pg.setConfigOption('background', '#1a1a2e')
pg.setConfigOption('foreground', '#e0e0e0')

app = QtWidgets.QApplication(sys.argv)
win = QtWidgets.QWidget()
win.setWindowTitle('ESP32 Data Analyzer')
win.resize(1300, 800)
win.setStyleSheet("background:#1a1a2e; color:#e0e0e0;")

root = QtWidgets.QVBoxLayout(win)
root.setContentsMargins(10, 10, 10, 10)
root.setSpacing(8)

# ── Toolbar ────────────────────────────────
toolbar = QtWidgets.QHBoxLayout()
root.addLayout(toolbar)

def btn(text, color):
    b = QtWidgets.QPushButton(text)
    b.setStyleSheet(f"QPushButton{{background:{color};color:white;border:none;"
                    f"padding:7px 14px;border-radius:4px;font-weight:bold;font-size:10pt;}}"
                    f"QPushButton:hover{{background:{color}bb;}}"
                    f"QPushButton:disabled{{background:#333;color:#666;}}")
    return b

btn_load    = btn('📂  Muat CSV', '#3498db')
btn_replay  = btn('▶  Replay', '#2ecc71')
btn_pause   = btn('⏸  Pause', '#e67e22')
btn_stop    = btn('⏹  Stop', '#e74c3c')
lbl_file    = QtWidgets.QLabel('Tiada fail dimuatkan')
lbl_file.setStyleSheet("color:#888; font-size:9pt;")
lbl_file.setAlignment(QtCore.Qt.AlignVCenter)

speed_label = QtWidgets.QLabel('Kelajuan:')
speed_label.setStyleSheet("color:#aaa; font-size:10pt;")
speed_box = QtWidgets.QComboBox()
speed_box.addItems(['0.5x', '1x', '2x', '5x', '10x', 'Max'])
speed_box.setCurrentIndex(1)
speed_box.setStyleSheet("background:#16213e; color:#e0e0e0; padding:4px; font-size:10pt;")

for w in [btn_load, btn_replay, btn_pause, btn_stop, speed_label, speed_box, lbl_file]:
    toolbar.addWidget(w)
toolbar.addStretch()

btn_pause.setEnabled(False)
btn_stop.setEnabled(False)

# ── Main area ──────────────────────────────
content = QtWidgets.QHBoxLayout()
root.addLayout(content)

# ── Kiri: Graf ─────────────────────────────
plot_widget = pg.GraphicsLayoutWidget()
content.addWidget(plot_widget, stretch=3)

p1 = plot_widget.addPlot(row=0, col=0, title="<b>Peratus (%) — Rekod / Replay</b>")
p1.showGrid(x=True, y=True, alpha=0.3)
p1.setLabel('left', '%')
p1.setYRange(0, 105)
curve_full = p1.plot(pen=pg.mkPen('#334', width=1.5))         # keseluruhan (latar)
curve_replay = p1.plot(pen=pg.mkPen('#00d4ff', width=2))      # replay
thresh_line = pg.InfiniteLine(pos=50, angle=0,
    pen=pg.mkPen('#ff6b6b', width=1, style=QtCore.Qt.DashLine))
p1.addItem(thresh_line)

plot_widget.nextRow()
p2 = plot_widget.addPlot(row=1, col=0, title="<b>Voltan (V)</b>")
p2.showGrid(x=True, y=True, alpha=0.3)
p2.setLabel('left', 'V')
p2.setLabel('bottom', 'Sampel')
p2.setYRange(0, 3.5)
curve_volt_full   = p2.plot(pen=pg.mkPen('#333', width=1.5))
curve_volt_replay = p2.plot(pen=pg.mkPen('#ff9f43', width=2))

plot_widget.nextRow()
p3 = plot_widget.addPlot(row=2, col=0, title="<b>Histogram Taburan (%)</b>")
p3.showGrid(x=True, y=True, alpha=0.3)
p3.setLabel('left', 'Kekerapan')
p3.setLabel('bottom', '%')
hist_bar = pg.BarGraphItem(x=[], height=[], width=4, brush='#9b59b6')
p3.addItem(hist_bar)

# Marker posisi replay
replay_line = pg.InfiniteLine(pos=0, angle=90,
    pen=pg.mkPen('#ffffff', width=2, style=QtCore.Qt.DotLine))
p1.addItem(replay_line)

# ── Kanan: Statistik ───────────────────────
right = QtWidgets.QVBoxLayout()
content.addLayout(right, stretch=1)

def stat_lbl(text, size=10, color='#aaa', bold=False):
    l = QtWidgets.QLabel(text)
    w = 'bold' if bold else 'normal'
    l.setStyleSheet(f"font-size:{size}pt; color:{color}; font-weight:{w};")
    l.setWordWrap(True)
    return l

def sep():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.HLine)
    f.setStyleSheet("color:#333;")
    return f

right.addWidget(stat_lbl('STATISTIK', 10, '#888', bold=True))
right.addWidget(sep())

stat_labels = {}
stat_defs = [
    ('total',          'Jumlah Rekod',      '#e0e0e0'),
    ('pct_min',        'Min %',             '#00d4ff'),
    ('pct_max',        'Maks %',            '#00d4ff'),
    ('pct_avg',        'Purata %',          '#00d4ff'),
    ('pct_std',        'Sisihan Piawai %',  '#00d4ff'),
    ('volt_min',       'Min Volt',          '#ff9f43'),
    ('volt_max',       'Maks Volt',         '#ff9f43'),
    ('volt_avg',       'Purata Volt',       '#ff9f43'),
    ('led_on_pct',     'LED ON %',          '#2ecc71'),
    ('led_off_pct',    'LED OFF %',         '#e74c3c'),
    ('max_on_streak',  'Streak ON terpanjang', '#2ecc71'),
    ('max_off_streak', 'Streak OFF terpanjang','#e74c3c'),
]

for key, label, color in stat_defs:
    row = QtWidgets.QHBoxLayout()
    lbl_k = stat_lbl(label + ':', 9, '#888')
    lbl_v = stat_lbl('—', 10, color, bold=True)
    lbl_v.setAlignment(QtCore.Qt.AlignRight)
    row.addWidget(lbl_k)
    row.addWidget(lbl_v)
    right.addLayout(row)
    stat_labels[key] = lbl_v

right.addWidget(sep())
right.addWidget(stat_lbl('POSISI REPLAY', 10, '#888', bold=True))
lbl_replay_pos  = stat_lbl('—', 10, '#e0e0e0')
lbl_replay_time = stat_lbl('—', 10, '#aaa')
lbl_replay_pct  = stat_lbl('—', 14, '#00d4ff', bold=True)
lbl_replay_volt = stat_lbl('—', 12, '#ff9f43', bold=True)
lbl_replay_led  = stat_lbl('—', 13, '#e0e0e0', bold=True)
for w in [lbl_replay_pos, lbl_replay_time, lbl_replay_pct, lbl_replay_volt, lbl_replay_led]:
    right.addWidget(w)
right.addStretch()

# ── State ──────────────────────────────────
rows_data     = []
replay_idx    = 0
replay_active = False
replay_paused = False
replay_thread = None

def update_stats(rows):
    st = analyze(rows)
    if not st: return
    fmt = {
        'total':          str(st['total']),
        'pct_min':        f"{st['pct_min']:.1f}%",
        'pct_max':        f"{st['pct_max']:.1f}%",
        'pct_avg':        f"{st['pct_avg']:.1f}%",
        'pct_std':        f"{st['pct_std']:.2f}",
        'volt_min':       f"{st['volt_min']:.2f} V",
        'volt_max':       f"{st['volt_max']:.2f} V",
        'volt_avg':       f"{st['volt_avg']:.2f} V",
        'led_on_pct':     f"{st['led_on_pct']:.1f}%  ({st['led_on_count']} rekod)",
        'led_off_pct':    f"{st['led_off_pct']:.1f}%  ({st['led_off_count']} rekod)",
        'max_on_streak':  f"{st['max_on_streak']} sampel",
        'max_off_streak': f"{st['max_off_streak']} sampel",
    }
    for k, v in fmt.items():
        stat_labels[k].setText(v)

def draw_full(rows):
    if not rows: return
    pcts  = [r['pct']  for r in rows]
    volts = [r['volt'] for r in rows]
    n = len(rows)
    curve_full.setData(range(n), pcts)
    curve_volt_full.setData(range(n), volts)
    p1.setXRange(0, n)
    p2.setXRange(0, n)
    # histogram
    counts, edges = np.histogram(pcts, bins=25, range=(0, 100))
    hist_bar.setOpts(x=edges[:-1], height=counts, width=(edges[1]-edges[0])*0.9)

def load_file():
    global rows_data
    path, _ = QtWidgets.QFileDialog.getOpenFileName(win, 'Buka CSV', os.path.dirname(LOG_FILE), 'CSV (*.csv)')
    if not path: path = LOG_FILE
    rows_data = load_csv(path)
    if not rows_data:
        lbl_file.setText('⚠ Fail kosong atau tidak dijumpai')
        return
    lbl_file.setText(f'✔ {os.path.basename(path)}  ({len(rows_data)} rekod)')
    draw_full(rows_data)
    update_stats(rows_data)
    curve_replay.setData([], [])
    curve_volt_replay.setData([], [])
    replay_line.setValue(0)
    btn_replay.setEnabled(True)

# ── Replay logic ───────────────────────────
replay_pcts  = []
replay_volts = []

def speed_factor():
    s = speed_box.currentText()
    return {'0.5x': 0.5, '1x': 1.0, '2x': 2.0, '5x': 5.0, '10x': 10.0, 'Max': 9999}[s]

def do_replay():
    global replay_active, replay_paused, replay_idx
    global replay_pcts, replay_volts
    replay_pcts  = []
    replay_volts = []
    replay_idx   = 0
    replay_active = True

    while replay_idx < len(rows_data) and replay_active:
        if replay_paused:
            time.sleep(0.05)
            continue
        row = rows_data[replay_idx]
        replay_pcts.append(row['pct'])
        replay_volts.append(row['volt'])

        # Update UI via signal
        update_replay_signal.emit(replay_idx, row)
        replay_idx += 1

        sf = speed_factor()
        if sf < 9999:
            time.sleep(0.1 / sf)

    replay_active = False
    QtCore.QMetaObject.invokeMethod(btn_replay, 'setEnabled', QtCore.Qt.QueuedConnection,
                                    QtCore.Q_ARG(bool, True))
    QtCore.QMetaObject.invokeMethod(btn_pause,  'setEnabled', QtCore.Qt.QueuedConnection,
                                    QtCore.Q_ARG(bool, False))
    QtCore.QMetaObject.invokeMethod(btn_stop,   'setEnabled', QtCore.Qt.QueuedConnection,
                                    QtCore.Q_ARG(bool, False))

class ReplaySignal(QtCore.QObject):
    trigger = QtCore.Signal(int, object)

update_replay_signal_obj = ReplaySignal()
update_replay_signal = update_replay_signal_obj.trigger

def on_replay_update(idx, row):
    curve_replay.setData(range(len(replay_pcts)), replay_pcts)
    curve_volt_replay.setData(range(len(replay_volts)), replay_volts)
    replay_line.setValue(idx)
    n = len(rows_data)
    lbl_replay_pos.setText(f'Sampel {idx+1} / {n}')
    lbl_replay_time.setText(f'Masa: {row["time"]}')
    lbl_replay_pct.setText(f'{row["pct"]:.1f}%')
    lbl_replay_volt.setText(f'{row["volt"]:.2f} V')
    led_color = '#2ecc71' if row['led'] == 'ON' else '#e74c3c'
    lbl_replay_led.setText(f'LED {row["led"]}')
    lbl_replay_led.setStyleSheet(f"font-size:13pt; font-weight:bold; color:{led_color};")

update_replay_signal.connect(on_replay_update)

def start_replay():
    global replay_thread, replay_active, replay_paused
    if not rows_data: return
    if replay_active: return
    replay_paused = False
    btn_replay.setEnabled(False)
    btn_pause.setEnabled(True)
    btn_stop.setEnabled(True)
    replay_thread = threading.Thread(target=do_replay, daemon=True)
    replay_thread.start()

def pause_replay():
    global replay_paused
    replay_paused = not replay_paused
    btn_pause.setText('▶  Resume' if replay_paused else '⏸  Pause')

def stop_replay():
    global replay_active
    replay_active = False
    btn_replay.setEnabled(True)
    btn_pause.setEnabled(False)
    btn_stop.setEnabled(False)
    btn_pause.setText('⏸  Pause')

btn_load.clicked.connect(load_file)
btn_replay.clicked.connect(start_replay)
btn_pause.clicked.connect(pause_replay)
btn_stop.clicked.connect(stop_replay)
btn_replay.setEnabled(False)

# Auto load jika fail ada
if os.path.exists(LOG_FILE):
    rows_data = load_csv(LOG_FILE)
    if rows_data:
        lbl_file.setText(f'✔ data_log.csv  ({len(rows_data)} rekod)')
        draw_full(rows_data)
        update_stats(rows_data)
        btn_replay.setEnabled(True)

win.show()
print("[ANALYZER] Sedia.")
app.exec_()
