@echo off
title Diskly - Empaquetador Profesional
cls

echo ===========================================
echo       DISKLY - CREADOR DE EJECUTABLE
echo ===========================================
echo.

:: Asegurar PyInstaller
pip install pyinstaller >nul 2>&1

echo [1/3] Limpiando archivos temporales...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [2/3] Compilando archivo único (.exe)...
echo      (Esto puede tardar un minuto)
python -m PyInstaller diskly.spec --noconfirm --clean

echo.
echo [3/3] Verificando resultado...
if exist "dist\Diskly.exe" (
    echo.
    echo ===========================================
    echo  ¡EXITO! El programa esta listo para compartir.
    echo  Ubicacion: dist\Diskly.exe
    echo ===========================================
) else (
    echo.
    echo [ERROR] Hubo un problema al crear el ejecutable.
    pause
)

pause
