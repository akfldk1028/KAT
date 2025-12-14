@echo off
echo === KAT 서버 시작 ===

echo [1/4] Express Server (8001) 시작...
start "KAT-Express-8001" cmd /k "cd /d D:\Data\18_KAT\KAT\frontend\KakaoTalk\server && npm start"

echo [2/4] React Client (3000) 시작...
start "KAT-React-3000" cmd /k "cd /d D:\Data\18_KAT\KAT\frontend\KakaoTalk\client && npm start"

echo [3/4] Agent API (8004) 시작...
start "KAT-Agent-8004" cmd /k "cd /d D:\Data\18_KAT\KAT\backend && .\venv_gpu\Scripts\activate && python -m uvicorn api.server:app --host 0.0.0.0 --port 8004 --reload"

echo [4/4] FastAPI App (8000) 시작...
start "KAT-App-8000" cmd /k "cd /d D:\Data\18_KAT\KAT\backend && .\venv_gpu\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo === 모든 서버 시작 완료 ===
echo 3000: React Client
echo 8000: FastAPI App
echo 8001: Express Server
echo 8004: Agent API
echo.
pause