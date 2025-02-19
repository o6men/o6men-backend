# Используем Python образ
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

# Копируем код
COPY . .

# Запускаем FastAPI сервер
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
