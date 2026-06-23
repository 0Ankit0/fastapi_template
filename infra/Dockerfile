FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies correctly using uv
RUN uv pip install --system .

# Copy application code
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

# Create non-root user
RUN groupadd --system app && useradd --system --gid app app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]