FROM python:3.12-slim


WORKDIR /app


RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml uv.lock ./


RUN pip install uv


RUN uv pip install --system --no-cache .


COPY . .


CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]