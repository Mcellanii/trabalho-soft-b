@echo off
rem Abre o Trabalho SOFT B com dois cliques, sem precisar do VS Code.
rem
rem O ambiente virtual fica FORA da pasta do projeto, em
rem     %LOCALAPPDATA%\TrabalhoSOFTB\venv
rem por dois motivos:
rem   1. um ambiente virtual so funciona no computador em que foi criado;
rem      copiado para outro PC (OneDrive, pendrive, zip) ele quebra;
rem   2. ele tem ~1 GB e ~27 mil arquivos, o que deixava a pasta enorme.
rem Na primeira execucao em cada computador este arquivo cria o ambiente sozinho.

setlocal
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\TrabalhoSOFTB\venv"

rem Ambiente pronto e funcionando? Entao so abre o programa.
if not exist "%VENV%\instalado.txt" goto preparar
"%VENV%\Scripts\python.exe" -c "" >nul 2>&1
if errorlevel 1 goto preparar
goto abrir

:preparar
echo Primeira execucao neste computador: preparando o ambiente.
echo Isso baixa cerca de 400 MB e leva alguns minutos. Aguarde...
echo.

rem Procura um Python instalado (3.12 e 3.13 sao os mais testados).
set "PY="
py -3.12 -c "" >nul 2>&1 && set "PY=py -3.12"
if not defined PY py -3.13 -c "" >nul 2>&1 && set "PY=py -3.13"
if not defined PY py -3.11 -c "" >nul 2>&1 && set "PY=py -3.11"
if not defined PY py -3 -c "" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "" >nul 2>&1 && set "PY=python"
if not defined PY goto sem_python

if exist "%VENV%" rmdir /s /q "%VENV%"
%PY% -m venv "%VENV%"
if errorlevel 1 goto falhou
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto falhou
echo ok> "%VENV%\instalado.txt"
echo.
echo Ambiente pronto.

:abrir
rem pythonw.exe abre a janela sem deixar um terminal preto aberto atras.
start "" "%VENV%\Scripts\pythonw.exe" main.py
exit /b 0

:sem_python
echo Python nao encontrado neste computador.
echo Instale o Python 3.12 em https://www.python.org/downloads/
echo (marque "Add python.exe to PATH") e abra este arquivo de novo.
echo.
pause
exit /b 1

:falhou
echo.
echo Nao foi possivel preparar o ambiente. Verifique a internet e tente de novo.
echo.
pause
exit /b 1
