@echo off
rem Double-click to open Quick Edit Image.
cd /d "%~dp0"

where python >nul 2>nul || (
    echo Chua cai Python. Tai tai https://www.python.org/downloads/ va tick "Add python.exe to PATH" khi cai.
    pause
    exit /b 1
)

python -c "import PIL" 2>nul || (
    echo Dang cai thu vien Pillow lan dau...
    python -m pip install -r requirements.txt || (
        echo Cai Pillow that bai.
        pause
        exit /b 1
    )
)

rem pythonw opens the app without leaving a console window behind.
start "" pythonw run.py
