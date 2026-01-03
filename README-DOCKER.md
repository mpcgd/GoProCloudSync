# GoPro Cloud Sync - Docker Build Guide

This guide explains how to build and deploy GoPro Cloud Sync containers for different platforms using Docker buildx.

## Dockerfile Overview

### Which Dockerfile to Use?

You only need **`Dockerfile.multiarch`**. This single Dockerfile can build for any platform:

- **`Dockerfile.multiarch`** - ✅ **Recommended** - Single file for all platforms

## Prerequisites

1. **Docker with buildx support** (included in modern Docker versions)
2. **Buildx setup** (run once):
   ```bash
   docker buildx create --use
   ```

## Building for Different Platforms

### Build for x86_64 (AMD/Intel)

```bash
docker buildx build \
  --platform linux/amd64 \
  -t gopro-sync-x86_64 \
  -f Dockerfile.multiarch \
  --load .
```

### Build for ARM64 (Raspberry Pi, Apple Silicon, etc.)

```bash
docker buildx build \
  --platform linux/arm64 \
  -t gopro-sync-arm64 \
  -f Dockerfile.multiarch \
  --load .
```

### Build for Native Platform (automatic detection)

```bash
docker buildx build \
  -t gopro-sync-native \
  -f Dockerfile.multiarch \
  --load .
```

## Deployment

### Save Container to Tar File

```bash
docker save gopro-sync-x86_64 -o gopro-sync-x86_64.tar
```

### Load and Run Container

```bash
# Load the container
docker load -i gopro-sync-x86_64.tar

# Run the container
docker run --rm \
  -v /path/to/your/backup:/downloads \
  -e GO_PRO_AUTH_TOKEN="your_gopro_token_here" \
  gopro-sync-x86_64
```

## Multi-Platform Build (Advanced)

Build for multiple platforms simultaneously:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t gopro-sync:multi-platform \
  -f Dockerfile.multiarch \
  --push  # Push to registry
```

## Troubleshooting

### "exec format error"

This occurs when the container architecture doesn't match the host. Solution:

1. **Check container architecture**:
   ```bash
   docker inspect --format='{{.Architecture}}' your-container
   ```

2. **Rebuild with correct platform**:
   ```bash
   docker buildx build --platform linux/amd64 -t correct-container -f Dockerfile.multiarch --load .
   ```

## Best Practices

1. **Use buildx** for proper cross-compilation
2. **Specify platform** explicitly with `--platform`
3. **Use `--load`** to load the image to local Docker
4. **Use tar files** for easy deployment
5. **Keep only `Dockerfile.multiarch`** for simplicity

With Docker buildx and `Dockerfile.multiarch`, you can build for any platform from a single Dockerfile!
