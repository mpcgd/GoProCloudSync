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

## Prerequisites

To use this tool, you need your **GoPro Cloud Auth Token**. There is no official public API for the cloud media library, so you must retrieve your session token:

1.  Log in to [GoPro Media Library](https://plus.gopro.com/media-library/) in your browser.
2.  Open **Developer Tools** (F12 or Right Click -> Inspect).
3.  Go to the **Network** tab.
4.  Refresh the page and look for a request to `api.gopro.com` (e.g., `search`, `user`, or `me`).
5.  Click on the request and find the **Request Headers**.
6.  Copy the token from the `Authorization` header. It usually looks like `Bearer <LONG_TOKEN_STRING>`. You only need the `<LONG_TOKEN_STRING>` part.
    *   *Alternatively, look for the `gp_access_token` cookie.*

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

### 4. Docker (Synology NAS / Server)

You can run this tool as a container, which is perfect for scheduled backups on a NAS.

**Build the Image:**
```bash
docker build -t gopro-sync .
```

**Run the Container:**
Map a local volume to `/data` in the container and pass the token.

```bash
docker run --rm \
  -v /path/to/local/backup:/data \
  -e GO_PRO_AUTH_TOKEN="YOUR_TOKEN_HERE" \
  gopro-sync --folder /data
```

**Synology NAS Setup via Task Scheduler:**
1.  Upload the image or pull it.
2.  Create a scheduled task with the `docker run` command above.
