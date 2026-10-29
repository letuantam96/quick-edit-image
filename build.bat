@echo off
rem Build dist\JokamQuimedit\ (exe + its files) and zip it into dist\JokamQuimedit-<version>.zip.
rem A folder build starts fast every time; a one-file exe would unpack itself on each launch.
cd /d "%~dp0"

for /f %%v in ('python bump_version.py') do set VER=%%v
echo Phien ban hien tai: %VER%
echo   1. Giu nguyen %VER%
echo   2. Sua loi nho      (patch: x.y.Z)
echo   3. Them tinh nang   (minor: x.Y.0)
echo   4. Thay doi lon     (major: X.0.0)
choice /c 1234 /n /m "Chon 1-4: "
if errorlevel 4 (set PART=major) else if errorlevel 3 (set PART=minor) else if errorlevel 2 (set PART=patch) else set PART=
if defined PART for /f %%v in ('python bump_version.py %PART%') do set VER=%%v
echo Build phien ban %VER%
echo.

python -m PyInstaller --version >nul 2>nul || (
    echo Dang cai PyInstaller...
    python -m pip install -r requirements.txt pyinstaller || goto :fail
)

python -m PyInstaller --noconfirm --clean --windowed --onedir --name JokamQuimedit ^
    --icon quick_edit_image\assets\icon.ico ^
    --add-data "quick_edit_image\assets;quick_edit_image\assets" ^
    run.py || goto :fail

set ZIP=dist\JokamQuimedit-%VER%.zip
if exist %ZIP% del %ZIP%
powershell -NoProfile -Command "Compress-Archive -Path dist\JokamQuimedit -DestinationPath %ZIP%" || goto :fail

echo.
echo Xong: %ZIP%
if defined PART echo Nho commit thay doi phien ban trong quick_edit_image\__init__.py.
pause
exit /b 0

:fail
echo.
echo Build loi.
pause
exit /b 1
