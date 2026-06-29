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

COPY infra/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Create non-root user
RUN groupadd --system app && \
    useradd --system --create-home --gid app app && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["./entrypoint.sh"]