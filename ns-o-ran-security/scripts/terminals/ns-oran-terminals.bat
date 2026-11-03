@echo off
REM ns-O-RAN 실험용 터미널 3개 띄우고 자동 배치
REM  C(ns-3) 왼쪽 크게 / A(e2term) 오른쪽 위 / B(xApp) 오른쪽 아래
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\nsoran-term\launch.ps1"
exit
