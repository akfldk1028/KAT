@echo off
REM KAT DualGuard Monitoring Stack 시작 스크립트
REM Prometheus + Loki + Grafana (PLG Stack)

echo ============================================
echo KAT DualGuard Monitoring Stack
echo ============================================
echo.

REM Docker 설치 확인
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker가 설치되어 있지 않습니다.
    echo Docker Desktop을 설치해주세요: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [INFO] Docker 확인 완료

REM monitoring 디렉토리로 이동
cd /d "%~dp0..\monitoring"

echo [INFO] Docker Compose 시작...
docker-compose up -d

if errorlevel 1 (
    echo [ERROR] Docker Compose 시작 실패
    pause
    exit /b 1
)

echo.
echo ============================================
echo 모니터링 스택 시작 완료!
echo ============================================
echo.
echo Grafana:     http://localhost:3001
echo             - ID: admin
echo             - PW: katadmin123
echo.
echo Prometheus:  http://localhost:9090
echo Loki:        http://localhost:3100
echo.
echo FastAPI 메트릭: http://localhost:8002/metrics
echo ============================================
echo.
pause
