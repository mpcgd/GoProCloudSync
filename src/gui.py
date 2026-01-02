import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import threading
import os
import sys

# Ensure project root is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import keyring
from src.sync import sync_account

SERVICE_ID = "gopro-cloud-sync"
ACCOUNT_ID = "auth_token"

class GoProSyncApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title="GoPro Cloud Sync")
        
        self.token_input = toga.PasswordInput(placeholder="Auth Token", style=Pack(flex=1))
        # Try load token
        try:
            stored_token = keyring.get_password(SERVICE_ID, ACCOUNT_ID)
            if stored_token:
                self.token_input.value = stored_token
        except:
            pass
            
        self.folder_input = toga.TextInput(readonly=True, placeholder="Target Folder", style=Pack(flex=1))
        self.folder_input.value = os.path.join(os.getcwd(), "GoProMedia") # Default
        
        folder_btn = toga.Button("Select Folder", on_press=self.select_folder)
        
        self.progress_bar = toga.ProgressBar(max=100)
        self.status_label = toga.Label("Ready", style=Pack(margin_top=10))
        
        start_btn = toga.Button("Start Sync", on_press=self.start_sync, style=Pack(margin_top=10))
        
        box = toga.Box(
            children=[
                toga.Box(children=[toga.Label("Token: "), self.token_input], style=Pack(direction=ROW, margin=5)),
                toga.Box(children=[self.folder_input, folder_btn], style=Pack(direction=ROW, margin=5)),
                start_btn,
                self.progress_bar,
                self.status_label
            ],
            style=Pack(direction=COLUMN, margin=10)
        )
        
        self.main_window.content = box
        self.main_window.show()

    async def select_folder(self, widget):
        path = await self.main_window.dialog(toga.SelectFolderDialog(title="Select Download Folder"))
        if path:
            self.folder_input.value = str(path)

    async def start_sync(self, widget):
        token = self.token_input.value
        folder = self.folder_input.value
        
        if not token:
            await self.main_window.dialog(toga.ErrorDialog("Error", "Please enter an Auth Token."))
            return
            
        # Save token
        try:
            keyring.set_password(SERVICE_ID, ACCOUNT_ID, token)
        except Exception as e:
            print(f"Keyring error: {e}")
            
        self.status_label.text = "Starting..."
        self.progress_bar.value = 0
        
        # Run in thread
        thread = threading.Thread(target=self.run_sync_thread, args=(token, folder))
        thread.start()
        
    def run_sync_thread(self, token, folder):
        def update_ui(msg, progress):
            def _update():
                self.status_label.text = msg
                if progress is not None:
                     self.progress_bar.value = progress
            self.app.loop.call_soon_threadsafe(_update)

        # Run sync
        sync_account(token, folder, callback=update_ui)
        
    def update_status(self, msg, progress):
        self.status_label.text = msg
        if progress is not None:
             self.progress_bar.value = progress

def main():
    return GoProSyncApp("GoPro Cloud Sync", "com.gopro.cloudsync")

if __name__ == '__main__':
    main().main_loop()
