@echo off
title LLM Gateway POC Server
echo.
echo =============================================
echo   LLM Gateway POC - Starting on port 8000
echo =============================================
echo.
cd /d %~dp0
set PYTHONPATH=%~dp0
echo   Root   : %~dp0
echo   Python : 
py --version
echo.
echo   Seeding demo data if needed...
if not exist "data\analytics.json" (
    py demo/seed_demo_data.py
)
echo.
echo   Swagger UI  ^> http://localhost:8000/docs
echo   Health      ^> http://localhost:8000/health
echo   Press Ctrl+C to stop.
echo.
py -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
pause
