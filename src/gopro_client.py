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

    def download_file(self, media_id, target_path, max_retries=3):
        # Fallback method using the zip/source endpoint which seems reliable
        url = f"{self.host}/media/x/zip/source"
        params = {
            "ids": media_id,
            "access_token": self.auth_token
        }
        cookies = {"gp_access_token": self.auth_token}

        for attempt in range(max_retries):
            try:
                logging.info(f"Downloading {media_id} to {target_path} (zip mode, attempt {attempt + 1}/{max_retries})...")

                with requests.get(url, params=params, headers=self._headers(), cookies=cookies, stream=True, timeout=30) as r:
                    if r.status_code != 200:
                        logging.error(f"Download failed for {media_id}: {r.status_code}")
                        if attempt < max_retries - 1:
                            logging.info(f"Retrying download for {media_id}...")
                            continue
                        return False

                    # Check content type to determine if it's a ZIP or direct file
                    content_type = r.headers.get('Content-Type', '')
                    is_zip = 'zip' in content_type or 'application/zip' in content_type

                    # Save to temporary file first
                    temp_file = target_path + ".temp"
                    with open(temp_file, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                    if is_zip:
                        # Handle ZIP format (for videos)
                        try:
                            with zipfile.ZipFile(temp_file, 'r') as z:
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
                                        if os.path.exists(target_path):
                                            os.remove(target_path)
                                        os.rename(extracted_full_path, target_path)
                                    return True

                        except zipfile.BadZipFile:
                            logging.warning("File was not a valid ZIP, treating as direct download")
                            # Fall through to direct file handling
                            pass
                        finally:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                    else:
                        # Handle direct file download (for photos)
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        os.rename(temp_file, target_path)
                        return True

                    # If we get here, ZIP extraction failed but we have the temp file
                    # Try to use it as a direct file (might be the actual media)
                    if os.path.exists(temp_file):
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        os.rename(temp_file, target_path)
                        return True

                # Success - return True
                return True

            except (requests.exceptions.RequestException, OSError) as e:
                logging.warning(f"Download attempt {attempt + 1} failed for {media_id}: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Retrying download for {media_id}...")
                    continue
                else:
                    logging.error(f"All download attempts failed for {media_id}")
                    return False

        return False

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
                with requests.get(direct_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(final_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return "downloaded"
            except Exception as e:
                logging.warning(f"Direct download failed: {e}. Falling back to zip method.")

        # Fallback to zip method
        if self.download_file(item["id"], final_path):
            # Handle .360 files that are actually ZIP files
            if filename.endswith('.360'):
                self._handle_360_file(final_path)
            return "downloaded"

        return "failed"

    def _handle_360_file(self, file_path):
        """
        Handle .360 files that are actually ZIP files.
        Renames to .zip and extracts the contents.
        """
        try:
            logging.info(f"Processing .360 file as ZIP: {file_path}")

            # Rename .360 to .zip
            zip_path = file_path + '.zip'
            os.rename(file_path, zip_path)

            # Extract the ZIP file
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Extract all files to the same directory
                z.extractall(os.path.dirname(zip_path))

                # Find the extracted media file (usually the first non-metadata file)
                extracted_files = z.namelist()
                media_files = [f for f in extracted_files
                              if not f.startswith('__') and not f.startswith('.')]

                if media_files:
                    # Get the first media file
                    first_media = media_files[0]
                    extracted_path = os.path.join(os.path.dirname(zip_path), first_media)

                    # Rename the extracted file to the original .360 name (but with proper extension)
                    final_name = os.path.splitext(file_path)[0] + os.path.splitext(first_media)[1]
                    final_path = os.path.join(os.path.dirname(file_path), final_name)

                    # Remove original .360.zip file
                    os.remove(zip_path)

                    # Rename extracted file to final name
                    if extracted_path != final_path:
                        os.rename(extracted_path, final_path)
                        logging.info(f"Extracted and renamed: {final_path}")
                    else:
                        logging.info(f"Extracted: {final_path}")

                    return True

            # Clean up the zip file if extraction failed
            if os.path.exists(zip_path):
                os.remove(zip_path)

        except Exception as e:
            logging.error(f"Failed to process .360 file {file_path}: {e}")
            # Restore original file if possible
            if os.path.exists(file_path + '.zip'):
                os.rename(file_path + '.zip', file_path)
            return False

        return False
