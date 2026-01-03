# GoPro Cloud Sync

A comprehensive tool to synchronize your GoPro Cloud media library to a local directory or NAS. This project provides a Python library, a Command Line Interface (CLI), a GUI application, and Docker support for various deployment scenarios.

## Features

-   **Smart Synchronization**: Mirrors your GoPro Cloud library to a local folder.
-   **Incremental Backup**: Checks file integrity (using file size) and skips already downloaded files.
-   **Direct & Fallback Downloads**: Attempts to find direct high-quality download links and falls back to the reliable zip-source method if needed.
-   **Multiple Interfaces**:
    -   **CLI**: Full-featured command-line tool for scripting and automation.
    -   **GUI**: Simple desktop interface (using Toga) for interactive use.
    -   **Library**: Reusable Python modules for custom integrations.
-   **Secure Credentials**: Supports system keyring for safe token storage.
-   **Docker Ready**: Includes a `Dockerfile` for easy deployment on Synology NAS or other container platforms.
-   **Automatic .360 File Handling**: Automatically detects and extracts GoPro .360 files that are actually ZIP archives

## File Handling Notes

**Automatic .360 File Processing:**
GoPro sometimes returns files with `.360` extensions that are actually ZIP archives. The sync process automatically:

1. **Detects** `.360` files that are ZIP archives
2. **Renames** them to `.zip` temporarily
3. **Extracts** the actual media files
4. **Cleans up** temporary ZIP files
5. **Renames** extracted media to proper filenames

This ensures you get actual video files (`.mp4`, `.mov`, etc.) instead of ZIP archives.

## Prerequisites

To use this tool, you need your **GoPro Cloud Auth Token**. There is no official public API for the cloud media library, so you must retrieve your session token:

1.  Log in to [GoPro Login](https://gopro.com/login) in your browser.
2.  Open **Developer Tools** (F12 or Right Click -> Inspect).
3.  Go to the **Network** tab.
4.  Refresh the page and filter for `api.gopro.com` or look for requests to `/search`, `/user`, or `/me`.
5.  Click on a request and view the **Request Headers**.
6.  Locate the connection cookies or the `Authorization` header.
    *   **Recommended**: Find the `gp_access_token` inside the `Cookie` header. It starts with `eyJ...`.
    *   *Alternatively*: Copy the token from `Authorization: Bearer <TOKEN>`.
    *   *Note*: The token provided should strictly be the JWT string (starting with `eyJ...`), without `Bearer` prefix or cookie name.

## Setup & Usage

### 1. Installation

**Using a Virtual Environment (Recommended):**

```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Command Line Interface (CLI)

The CLI is ideal for cron jobs or headless servers.

**First Run (Save Token):**
You can opt to save the token to your system keyring to avoid passing it every time.

```bash
# Replace YOUR_TOKEN_HERE with the token retrieved in Prerequisites
python -m src.cli --token "YOUR_TOKEN_HERE" --save-token --folder ./my_gopro_backup
```

**Subsequent Runs:**
Once the token is saved, you only need to specify the folder (if different from default).

```bash
python -m src.cli --folder ./my_gopro_backup
```

**Using Environment Variables:**
You can also provide the token via the `GO_PRO_AUTH_TOKEN` environment variable.

```bash
export GO_PRO_AUTH_TOKEN="YOUR_TOKEN_HERE"
python -m src.cli --folder ./my_gopro_backup
```

### 3. Graphical User Interface (GUI)

For a visual experience, use the Toga-based GUI.

```bash
python -m src.gui
```
-   Enter your Auth Token.
-   Select your target download folder.
-   Click **Start Sync**.

### 4. Docker (Multi-Platform Support)

You can run this tool as a container, which is perfect for scheduled backups on NAS devices, servers, or any platform.

#### Dockerfile Overview

You only need **`Dockerfile.multiarch`** - a single Dockerfile that supports all platforms including x86_64 (AMD/Intel) and ARM64.

#### Prerequisites

1. **Docker with buildx support** (included in modern Docker versions)
2. **Buildx setup** (run once):
   ```bash
   docker buildx create --use
   ```

#### Building for Different Platforms

**Build for x86_64 (AMD/Intel):**
```bash
docker buildx build \
  --platform linux/amd64 \
  -t gopro-sync-x86_64 \
  -f Dockerfile.multiarch \
  --load .
```

**Build for ARM64 (Raspberry Pi, Apple Silicon, etc.):**
```bash
docker buildx build \
  --platform linux/arm64 \
  -t gopro-sync-arm64 \
  -f Dockerfile.multiarch \
  --load .
```

**Build for Native Platform (automatic detection):**
```bash
docker buildx build \
  -t gopro-sync-native \
  -f Dockerfile.multiarch \
  --load .
```

#### Deployment

**Save Container to Tar File:**
```bash
docker save gopro-sync-x86_64 -o gopro-sync-x86_64.tar
```

**Load and Run Container:**
```bash
# Load the container
docker load -i gopro-sync-x86_64.tar

# Run the container
docker run --rm \
  -v /path/to/your/backup:/downloads \
  -e GO_PRO_AUTH_TOKEN="YOUR_TOKEN_HERE" \
  gopro-sync-x86_64
```

#### Multi-Platform Build (Advanced)

Build for multiple platforms simultaneously:
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t gopro-sync:multi-platform \
  -f Dockerfile.multiarch \
  --push  # Push to registry
```

#### Troubleshooting

**"exec format error":**
This occurs when the container architecture doesn't match the host. Solution:
1. Check container architecture: `docker inspect --format='{{.Architecture}}' your-container`
2. Rebuild with correct platform: `docker buildx build --platform linux/amd64 -t correct-container -f Dockerfile.multiarch --load .`

#### Best Practices

1. **Use buildx** for proper cross-compilation
2. **Specify platform** explicitly with `--platform`
3. **Use `--load`** to load the image to local Docker
4. **Use tar files** for easy deployment
5. **Keep only `Dockerfile.multiarch`** for simplicity

**Synology NAS Setup via Task Scheduler:**
1. Upload the image or pull it
2. Create a scheduled task with the `docker run` command above
