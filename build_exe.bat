@echo off
echo ============================================
echo  Diskly - Build .exe con PyInstaller
echo ============================================
echo.
echo [1/2] Limpiando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [2/2] Compilando...
python -m PyInstaller diskly.spec --noconfirm --clean

echo.
echo ============================================
if exist dist\Diskly\Diskly.exe (
    echo  BUILD EXITOSO!
    echo  Ejecutable: dist\Diskly\Diskly.exe
) else (
    echo  BUILD FALLIDO - revisa los mensajes arriba
)
echo ============================================
pause
