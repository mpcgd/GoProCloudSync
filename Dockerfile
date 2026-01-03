# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    upx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pyinstaller

COPY src/ ./src/

# Build standalone binary
# --clean: clean cache
# --strip: strip symbols (only works on some platforms/versions, but UPX does the heavy lifting)
RUN pyinstaller --onefile --clean --name gopro-sync --paths . src/cli.py && \
    upx --best --lzma /app/dist/gopro-sync

# Stage 2: Final minimal image
FROM debian:stable-slim

WORKDIR /app

# Install runtime dependencies
# libstdc++: for PyInstaller binary
# ca-certificates: ESSENTIAL for HTTPS requests to GoPro API
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/dist/gopro-sync /app/gopro-sync

# Create a directory for downloads
RUN mkdir -p /downloads

# Token should be passed at runtime for security
# Run example: docker run -e GO_PRO_AUTH_TOKEN="your_token" -v /downloads:/downloads gopro-sync

# Default command
ENTRYPOINT ["/app/gopro-sync"]
CMD ["--folder", "/downloads"]
