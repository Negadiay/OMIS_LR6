import uvicorn
import os
import sys

# Добавляем путь, чтобы Python видел пакет backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Запуск системы...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)