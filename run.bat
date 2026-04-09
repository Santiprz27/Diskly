@echo off
echo Iniciando Diskly...
echo " ,------.  ,--.       ,--.    ,--.          "
echo " |  .-.  \ `--' ,---. |  |,-. |  |,--. ,--. "
echo " |  |  \  :,--.(  .-' |     / |  | \  '  /  "
echo " |  '--'  /|  |.-'  `)|  \  \ |  |  \   '   "
echo " `-------' `--'`----' `--'`--'`--'.-'  /    "
echo "                                  `---'     "

cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Diskly termino con error. Revisa el traceback arriba.
    echo  Para reinstalar dependencias:
    echo    pip install -r requirements.txt
    echo ============================================================
    pause
)
