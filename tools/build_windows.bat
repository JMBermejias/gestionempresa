@echo off
echo ============================================
echo   Gestion Empresa - Generador Windows .exe
echo ============================================
echo.
echo Comprobando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python 3.8+ desde python.org
    pause
    exit /b 1
)
echo.
echo Instalando PyInstaller...
pip install pyinstaller >nul 2>&1
echo.
echo Generando .exe...
python "%~dp0build_windows.py"
echo.
if exist "%~dp0dist\GestionEmpresa.exe" (
    echo ============================================
    echo   INSTALADOR GENERADO:
    echo   %~dp0dist\GestionEmpresa.exe
    echo ============================================
    echo.
    echo Copia GestionEmpresa.exe a donde quieras ejecutarlo.
    echo Al ejecutarlo se abrira el navegador automaticamente.
    echo Los datos se guardan en %%APPDATA%%\GestionEmpresa
) else (
    echo ERROR: No se pudo generar el .exe
)
echo.
pause
