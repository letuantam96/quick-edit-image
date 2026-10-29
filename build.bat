@echo off
rem Build dist\JokamQuimedit\ (exe + its files) and zip it into dist\JokamQuimedit.zip.
rem A folder build starts fast every time; a one-file exe would unpack itself on each launch.
cd /d "%~dp0"

python -m PyInstaller --version >nul 2>nul || (
    echo Dang cai PyInstaller...
    python -m pip install -r requirements.txt pyinstaller || exit /b 1
)

python -m PyInstaller --noconfirm --clean --windowed --onedir --name JokamQuimedit ^
    --icon quick_edit_image\assets\icon.ico ^
    --add-data "quick_edit_image\assets;quick_edit_image\assets" ^
    run.py || exit /b 1

if exist dist\JokamQuimedit.zip del dist\JokamQuimedit.zip
powershell -NoProfile -Command "Compress-Archive -Path dist\JokamQuimedit -DestinationPath dist\JokamQuimedit.zip" || exit /b 1

echo.
echo Xong: dist\JokamQuimedit.zip
