import argparse
import os
import sys
import logging
try:
    import keyring
except ImportError:
    keyring = None

from .sync import sync_account

SERVICE_ID = "gopro-cloud-sync"
ACCOUNT_ID = "auth_token"

def get_token():
    # 1. Env Var
    token = os.environ.get("GO_PRO_AUTH_TOKEN")
    if token:
        return token
        
    # 2. Keyring (if available)
    if keyring:
        try:
            token = keyring.get_password(SERVICE_ID, ACCOUNT_ID)
            if token:
                return token
        except Exception as e:
            logging.warning(f"Keyring access failed: {e}")
    else:
        logging.debug("Keyring not installed, skipping keyring lookup.")
        
    return None

def set_token(token):
    if not keyring:
        logging.error("Keyring module not installed. Cannot save token.")
        return

    try:
        keyring.set_password(SERVICE_ID, ACCOUNT_ID, token)
        print("Token saved to keyring.")
    except Exception as e:
        logging.error(f"Failed to save token to keyring: {e}")

def main():
    parser = argparse.ArgumentParser(description="GoPro Cloud Sync")
    parser.add_argument("--folder", help="Target folder for sync")
    parser.add_argument("--token", help="GoPro Cloud Auth Token")
    parser.add_argument("--save-token", action="store_true", help="Save the provided token to keyring")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    token = args.token
    if token and args.save_token:
        set_token(token)
    
    if not token:
        token = get_token()
        
    if not token:
        print("Error: No auth token found. Provide it via --token or GO_PRO_AUTH_TOKEN env var.")
        sys.exit(1)
        
    folder = args.folder
    if not folder:
        # Default? Cur dir?
        folder = os.getcwd()
        print(f"No folder specified. Using current directory: {folder}")
        
    print(f"Syncing to {folder}...")
    success = sync_account(token, folder)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
