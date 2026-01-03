# Stage 1: Builder
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev upx

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pyinstaller

COPY src/ ./src/

# Build standalone binary and compress with UPX
# --clean: clean cache
# --strip: strip symbols (only works on some platforms/versions, but UPX does the heavy lifting)
RUN pyinstaller --onefile --clean --name gopro-sync --paths . src/cli.py && \
    upx --best --lzma /app/dist/gopro-sync

# Stage 2: Final minimal image
FROM alpine:latest

WORKDIR /app

# Install runtime dependencies
# libstdc++: for PyInstaller binary
# ca-certificates: ESSENTIAL for HTTPS requests to GoPro API
RUN apk add --no-cache libstdc++ ca-certificates

# Copy binary from builder
COPY --from=builder /app/dist/gopro-sync /app/gopro-sync

# Create a directory for downloads
RUN mkdir -p /downloads

# Token should be passed at runtime for security
# Run example: docker run -e GO_PRO_AUTH_TOKEN="your_token" -v /downloads:/downloads gopro-sync

# Default command
ENTRYPOINT ["/app/gopro-sync"]
CMD ["--folder", "/downloads"]
