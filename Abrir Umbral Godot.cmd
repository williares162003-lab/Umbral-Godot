@echo off
setlocal
title Umbral - Abrir Godot
set "GODOT=C:\Users\WILLIAM\Documents\Codex\Herramientas\Godot\4.6.3-standard\Godot_v4.6.3-stable_win64.exe"
for %%I in ("%~dp0.") do set "PROJECT=%%~fI"

if not exist "%GODOT%" (
  echo No se encontro Godot en:
  echo %GODOT%
  pause
  exit /b 1
)

if not exist "%PROJECT%\project.godot" (
  echo No se encontro project.godot en:
  echo %PROJECT%
  pause
  exit /b 1
)

echo Abriendo Umbral en Godot...
echo Proyecto: %PROJECT%
pushd "%PROJECT%"
"%GODOT%" --editor --path "%PROJECT%"
set "GODOT_EXIT=%ERRORLEVEL%"
popd

if not "%GODOT_EXIT%"=="0" (
  echo.
  echo Godot termino con el codigo %GODOT_EXIT%.
  echo Toma una captura de este mensaje para poder revisarlo.
  pause
)

exit /b %GODOT_EXIT%
