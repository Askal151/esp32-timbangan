@echo off
setlocal

set PIO="C:\Users\Dell\.platformio\penv\Scripts\platformio.exe"
cd /d "%~dp0"

if "%1"=="build"   goto build
if "%1"=="upload"  goto upload
if "%1"=="monitor" goto monitor
if "%1"=="um"      goto um
if "%1"=="clean"   goto clean
if "%1"=="ports"   goto ports
if "%1"=="libs"    goto libs
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
echo [ERROR] Arahan tidak sah.
goto end

:: ─────────────────────────────────────────
:build
echo.
echo [BUILD] Compiling...
%PIO% run
goto end

:upload
echo.
echo [UPLOAD] Compiling dan upload ke ESP32...
%PIO% run --target upload
goto end

:monitor
echo.
echo [MONITOR] Serial Monitor - tekan Ctrl+C untuk keluar...
%PIO% device monitor
goto end

:um
echo.
echo [UPLOAD + MONITOR] Upload kemudian buka monitor...
%PIO% run --target upload
if %errorlevel%==0 %PIO% device monitor
goto end

:clean
echo.
echo [CLEAN] Membuang fail build...
%PIO% run --target clean
goto end

:ports
echo.
echo [PORTS] Port COM yang tersedia:
%PIO% device list
goto end

:libs
echo.
echo [LIBS] Memasang semula library...
%PIO% lib install
goto end

:unknown
echo [ERROR] Arahan tidak dikenali: %1
echo Jalankan: pio.bat help
goto end

:: ─────────────────────────────────────────
:end
echo.
endlocal
