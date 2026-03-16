@echo off
setlocal enabledelayedexpansion

set PIO=C:\Users\Dell\.platformio\penv\Scripts\platformio.exe
cd /d "%~dp0"

if "%1"=="build"   goto build
if "%1"=="upload"  goto upload
if "%1"=="monitor" goto monitor
if "%1"=="um"      goto um
if "%1"=="clean"   goto clean
if "%1"=="ports"   goto ports
if "%1"=="libs"    goto libs
if "%1"=="kill"    goto kill
if "%1"=="help"    goto help
if not "%1"==""    goto unknown

:: ─── Menu interaktif ──────────────────────
:help
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   ESP32 PlatformIO Build Tool        ║
echo  ╚══════════════════════════════════════╝
echo.
echo   build     - Compile sahaja
echo   upload    - Compile + upload ke ESP32
echo   monitor   - Buka Serial Monitor (115200)
echo   um        - Upload + terus buka monitor
echo   clean     - Padam hasil build
echo   ports     - Senarai port COM yang ada
echo   libs      - Pasang semula library
echo   kill      - Kill semua proses yang pegang port COM
echo.
echo  Guna:  pio.bat ^<arahan^>
echo  Atau double-click pio.bat untuk menu
echo.
if not "%1"=="" goto end
set /p CMD= Pilih arahan:
if "%CMD%"=="build"   goto build
if "%CMD%"=="upload"  goto upload
if "%CMD%"=="monitor" goto monitor
if "%CMD%"=="um"      goto um
if "%CMD%"=="clean"   goto clean
if "%CMD%"=="ports"   goto ports
if "%CMD%"=="libs"    goto libs
if "%CMD%"=="kill"    goto kill
echo [ERROR] Arahan tidak sah.
goto end

:: ─── Auto detect ESP32 port ───────────────
:find_port
set ESP_PORT=
for /f "usebackq" %%A in (`powershell -nologo -noprofile -command "$out = & '%PIO%' device list 2>$null; $lines = $out -split '\n'; $port = ''; for($i=0;$i-lt$lines.Count;$i++){if($lines[$i] -match '^COM\d+'){$port=$lines[$i].Trim()}; if($lines[$i] -match 'CP210|CH340|CH341|FTDI' -and $port){Write-Output $port; $port=''; break}}; exit 0"`) do (
    set ESP_PORT=%%A
)
if "!ESP_PORT!"=="" (
    echo [WARN] ESP32 tidak dijumpai secara auto, cuba port USB pertama...
    for /f "usebackq" %%A in (`powershell -nologo -noprofile -command "$out = & '%PIO%' device list 2>$null; $lines = $out -split '\n'; foreach($l in $lines){if($l -match '^COM\d+'){Write-Output $l.Trim(); break}}"`) do (
        set ESP_PORT=%%A
    )
)
if "!ESP_PORT!"=="" (
    echo [ERROR] Tiada port COM dijumpai. Pastikan ESP32 disambung.
    goto end
)
echo [PORT] ESP32 dijumpai di: !ESP_PORT!
goto :eof

:: ─────────────────────────────────────────
:build
echo.
echo [BUILD] Compiling...
"%PIO%" run
goto end

:upload
echo.
call :find_port
if "!ESP_PORT!"=="" goto end
echo [UPLOAD] Compiling dan upload ke !ESP_PORT!...
"%PIO%" run --target upload --upload-port !ESP_PORT!
goto end

:monitor
echo.
call :find_port
if "!ESP_PORT!"=="" goto end
echo [MONITOR] Serial Monitor pada !ESP_PORT! - tekan Ctrl+C untuk keluar...
"%PIO%" device monitor --port !ESP_PORT! --baud 115200
goto end

:um
echo.
call :find_port
if "!ESP_PORT!"=="" goto end
echo [UPLOAD + MONITOR] Upload ke !ESP_PORT! kemudian buka monitor...
"%PIO%" run --target upload --upload-port !ESP_PORT!
if !errorlevel!==0 "%PIO%" device monitor --port !ESP_PORT! --baud 115200
goto end

:clean
echo.
echo [CLEAN] Membuang fail build...
"%PIO%" run --target clean
goto end

:ports
echo.
echo [PORTS] Port COM yang tersedia:
"%PIO%" device list
goto end

:libs
echo.
echo [LIBS] Memasang semula library...
"%PIO%" lib install
goto end

:kill
echo.
echo [KILL] Menutup semua proses yang mungkin pegang port COM...
taskkill /f /im python.exe >nul 2>&1 && echo  - python.exe ditutup || echo  - python.exe tiada
taskkill /f /im platformio.exe >nul 2>&1 && echo  - platformio.exe ditutup || echo  - platformio.exe tiada
taskkill /f /im miniterm.exe >nul 2>&1 && echo  - miniterm.exe ditutup || echo  - miniterm.exe tiada
taskkill /f /im putty.exe >nul 2>&1 && echo  - putty.exe ditutup || echo  - putty.exe tiada
echo [KILL] Selesai. Port COM kini bebas.
goto end

:unknown
echo [ERROR] Arahan tidak dikenali: %1
echo Jalankan: pio.bat help
goto end

:: ─────────────────────────────────────────
:end
echo.
endlocal
