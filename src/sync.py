import os
import logging
from .gopro_client import GoProPlus

def sync_account(auth_token, target_folder, callback=None):
    """
    Syncs the GoPro Cloud account to the target folder.
    callback(message, progress_percent) is an optional function for GUI updates.
    """
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        
    client = GoProPlus(auth_token)
    
    if callback: callback("Validating token...", 0)
    if not client.validate():
        logging.error("Invalid token.")
        if callback: callback("Invalid token.", 0)
        return False

    if callback: callback("Fetching media list...", 5)
    media_list = client.get_media_list()
    logging.info(f"Found {len(media_list)} items in cloud.")
    
    total_items = len(media_list)
    downloaded = 0
    skipped = 0
    failed = 0
    
    for i, item in enumerate(media_list):
        progress = 10 + int((i / total_items) * 90)
        filename = item.get("filename") or f"{item['id']}.mp4" # fallback
        if callback: callback(f"Processing {filename}...", progress)
        
        logging.info(f"Processing {i+1}/{total_items}: {filename}")
        
        try:
            success = client.download_media_item(item, target_folder)
            if success:
                downloaded += 1 # Or skipped if it existed, client returns True for skip too
            else:
                failed += 1
        except Exception as e:
            logging.error(f"Error syncing {filename}: {e}")
            failed += 1
            
    if callback: callback("Sync complete.", 100)
    logging.info(f"Sync finished. Processed {total_items}. Failed: {failed}")
    return True
