@echo off
title Lanzador Diskly
cls

echo ===========================================
echo            DISKLY - ANALIZADOR
echo ===========================================

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No tienes Python instalado.
    echo Por favor, instala Python desde python.org y vuelve a intentarlo.
    pause
    exit
)

:: 2. Instalar dependencias
echo [1/2] Verificando e instalando librerias necesarias...
pip install -r requirements.txt

:: 3. Iniciar Diskly
echo [2/2] Iniciando aplicacion...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ===========================================
    echo  Diskly se detuvo inesperadamente.
    echo ===========================================
    pause
)
