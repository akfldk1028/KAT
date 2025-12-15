@echo off
cd /d D:\Data\18_KAT\KAT\backend
call venv_gpu\Scripts\activate.bat
python -m uvicorn api.server:app --host 0.0.0.0 --port 8004 --reload
