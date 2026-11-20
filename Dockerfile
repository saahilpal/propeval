FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-dev

COPY backend /app/backend
COPY suites /app/suites
COPY fixtures /app/fixtures

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
