@echo off
REM KAT DualGuard Monitoring Stack 중지 스크립트

echo ============================================
echo KAT DualGuard Monitoring Stack 중지
echo ============================================
echo.

cd /d "%~dp0..\monitoring"

echo [INFO] Docker Compose 중지...
docker-compose down

echo.
echo [INFO] 모니터링 스택이 중지되었습니다.
echo.
pause
