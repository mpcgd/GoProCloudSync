import os
import sys
import requests
import logging
import zipfile

class GoProPlus:
    def __init__(self, auth_token):
        self.base = "api.gopro.com"
        self.host = "https://{}".format(self.base)
        self.auth_token = auth_token
        self.user_id = None # derived or optional, strictly speaking auth_token is often enough but cookies might need it.
        # However, the previous code used `gp_access_token` cookie.
        # I will fetch user info to get the user_id if needed or just use the token.
    
    def _headers(self):
        return {
            "Accept": "application/vnd.gopro.jk.media+json; version=2.0.0",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Authorization": f"Bearer {self.auth_token}"
        }

    def validate(self):
        # We can also get self.user_id here if we call a user endpoint
        url = f"{self.host}/me"
        # The previous code used /media/user with cookies.
        # Let's try to use Bearer token header which is more standard.
        # If that fails, I might need to simulate cookies.
        try:
             # Try standard OAuth2 style first
            resp = requests.get(url, headers=self._headers())
            if resp.status_code == 200:
                data = resp.json()
                self.user_id = data.get("id") or data.get("user_id")
                return True
        except Exception as e:
            logging.debug(f"Validation via /me failed: {e}")

        # Fallback to the method from the referenced repo
        # It used cookies: gp_access_token=<token>
        # And endpoint /media/user
        return self._validate_legacy()

    def _validate_legacy(self):
        url = f"{self.host}/media/user"
        cookies = {"gp_access_token": self.auth_token}
        resp = requests.get(url, headers=self._headers(), cookies=cookies)
        if resp.status_code == 200:
            return True
        logging.error(f"Validation failed. Status: {resp.status_code}, Body: {resp.text}")
        return False

    def get_media_list(self, pages=sys.maxsize, per_page=30):
        url = f"{self.host}/media/search"
        media_items = []
        current_page = 1
        
        while True:
            params = {
                "per_page": per_page,
                "page": current_page,
                "fields": "id,created_at,content_title,filename,file_extension,file_size,variations,type", 
                # Request variations to see if we have direct links
            }
            
            # Using cookies as the reference implementation did, just to be safe
            cookies = {"gp_access_token": self.auth_token}
            
            resp = requests.get(url, params=params, headers=self._headers(), cookies=cookies)
            
            if resp.status_code != 200:
                logging.error(f"Failed to get media list: {resp.status_code} - {resp.text}")
                break
                
            data = resp.json()
            embedded = data.get("_embedded", {})
            page_media = embedded.get("media", [])
            
            if not page_media:
                break
                
            media_items.extend(page_media)
            logging.info(f"Fetched page {current_page}, found {len(page_media)} items.")
            
            current_page += 1
            if current_page > pages:
                break
                
            # Check total pages
            # The reference code checked _pages.total_pages
            total_pages = data.get("_pages", {}).get("total_pages", 0)
            if current_page > total_pages:
                break

        return media_items

    def get_download_url(self, media_item):
        # Try to find a direct high-res download URL
        # 'variations' usually contains different qualities.
        # We want 'source' or highest quality.
        variations = media_item.get("variations", [])
        
        # Sort or find the best one.
        # Often 'source' is the type.
        for v in variations:
            if v.get("type") == "source" or v.get("label") == "source":
                 return v.get("url")
        
        # Fallback: check other variations
        # If no source, take the 'high_res' or similar?
        # Let's inspect variations structure in future if needed.
        # For now, if no variations, we might rely on ids.
        
        if variations:
             # Return the first one if source not found??
             # Better safe than sorry, maybe return None and fall back to zip/source
             pass
             
        return None

    def download_file(self, media_id, target_path):
        # Fallback method using the zip/source endpoint which seems reliable
        url = f"{self.host}/media/x/zip/source"
        params = {
            "ids": media_id,
            "access_token": self.auth_token
        }
        cookies = {"gp_access_token": self.auth_token}

        # Verify if target exists (Caller should have checked this, but if we are here we likely want to overwrite or it's a new file)
        # if os.path.exists(target_path):
        #    logging.info(f"File {target_path} already exists. Skipping.")
        #    return True
        # REMOVED to allow simple overwrites if caller determined it's needed.

        logging.info(f"Downloading {media_id} to {target_path} (zip mode)...")
        
        with requests.get(url, params=params, headers=self._headers(), cookies=cookies, stream=True) as r:
            if r.status_code != 200:
                logging.error(f"Download failed for {media_id}: {r.status_code}")
                return False
            
            # This returns a ZIP file. We might want to save it as .zip or stream unzip it.
            # Mirroring usually implies keeping the original format.
            # If the source gives a zip, we get a zip.
            # If the user wants the raw file (mp4/jpg), we need to extract it.
            
            # Let's save as .zip for safety first, or unzip?
            # User said "mirror ... files". Usually means .mp4 or .jpg.
            # If I download 1 file via zip/source, it's a zip containing one file.
            
            # I will implement unzip logic.
            # Save to temporary zip, then extract, then delete zip.
            
            temp_zip = target_path + ".zip"
            with open(temp_zip, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
    # Unzip
            try:
                with zipfile.ZipFile(temp_zip, 'r') as z:
                    names = z.namelist()
                    # Filter for likely media files (ignore __MACOSX, hidden files)
                    media_files = [n for n in names if not n.startswith('__') and not n.startswith('.') and '/' not in n]
                    
                    if media_files:
                        # Extract only the first valid media file
                        extracted_name = media_files[0]
                        target_dir = os.path.dirname(target_path)
                        z.extract(extracted_name, target_dir)
                        
                        extracted_full_path = os.path.join(target_dir, extracted_name)
                        
                        # Rename if the extracted filename doesn't match our target specific path
                        if extracted_full_path != target_path:
                            # Remove target if it exists (though check earlier handled this, race condition possible)
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            os.rename(extracted_full_path, target_path)
                            
            except zipfile.BadZipFile:
                logging.error("Downloaded file is not a valid zip.")
                return False
            finally:
                if os.path.exists(temp_zip):
                    os.remove(temp_zip)
                    
        return True

    def download_media_item(self, item, target_dir):
        # Wrapper that handles filename and checks
        filename = item.get("filename")
        if not filename:
             # construct from id + extension
             ext = item.get("file_extension", "mp4")
             filename = f"{item['id']}.{ext}"

        final_path = os.path.join(target_dir, filename)
        
        if os.path.exists(final_path):
            # Check integrity? Size?
            remote_size = item.get("file_size")
            if remote_size:
                local_size = os.path.getsize(final_path)
                if local_size == int(remote_size):
                    logging.info(f"Skipping {filename}, exists and size matches")
                    return "skipped"
        
        # Try direct link first (optimization)
        direct_url = self.get_download_url(item)
        if direct_url:
            logging.info(f"Downloading {filename} via direct link...")
            try:
                with requests.get(direct_url, stream=True) as r:
                    r.raise_for_status()
                    with open(final_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return "downloaded"
            except Exception as e:
                logging.warning(f"Direct download failed: {e}. Falling back to zip method.")

        # Fallback to zip method
        if self.download_file(item["id"], final_path):
            return "downloaded"
        
        return "failed"
