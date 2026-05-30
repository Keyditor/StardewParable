@echo off
echo Iniciando o Servidor Backend (FastAPI)...
echo.

cd backend

:: Verifica se a porta 8000 (padrão) já está em uso, mas ignora erros
echo Iniciando Uvicorn na porta 8000...
uvicorn main:app --reload --host localhost --port 8000

pause
