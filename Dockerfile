FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Env variable for token (optional in build, passed in run)
ENV GO_PRO_AUTH_TOKEN=""
ENV PYTHONUNBUFFERED=1

# Default command runs the CLI
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--help"]
