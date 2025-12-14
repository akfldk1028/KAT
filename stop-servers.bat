@echo off
echo === KAT 서버 종료 ===

echo 포트 3000 종료...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do taskkill /PID %%a /F 2>nul

echo 포트 8000 종료...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F 2>nul

echo 포트 8001 종료...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do taskkill /PID %%a /F 2>nul

echo 포트 8004 종료...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8004 ^| findstr LISTENING') do taskkill /PID %%a /F 2>nul

echo.
echo === 모든 서버 종료 완료 ===
pause