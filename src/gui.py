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
        self.is_syncing = False
        self.stop_requested = False
        
        # Token UI
        self.token_input = toga.PasswordInput(placeholder="Auth Token", style=Pack(flex=1))
        
        # Check Env first
        env_token = os.environ.get("GO_PRO_AUTH_TOKEN")
        if env_token:
            self.token_input.value = env_token
            # Maybe hint it's from env?
            token_label_text = "Token (Env):"
        else:
            token_label_text = "Token:"
            # Try load from keyring
            try:
                stored_token = keyring.get_password(SERVICE_ID, ACCOUNT_ID)
                if stored_token:
                    self.token_input.value = stored_token
            except:
                pass
        
        self.delete_token_btn = toga.Button("Clear Saved", on_press=self.delete_token, style=Pack(margin_left=5))

        # Folder UI
        self.folder_input = toga.TextInput(readonly=True, placeholder="Target Folder", style=Pack(flex=1))
        self.folder_input.value = os.path.join(os.getcwd(), "GoProMedia") # Default
        
        folder_btn = toga.Button("Select Folder", on_press=self.select_folder)
        
        # Controls
        self.progress_bar = toga.ProgressBar(max=100)
        self.status_label = toga.Label("Ready", style=Pack(margin_top=10))
        
        self.start_stop_btn = toga.Button("Start Sync", on_press=self.toggle_sync, style=Pack(margin_top=10, flex=1))
        
        # Layout
        token_box = toga.Box(children=[toga.Label(token_label_text), self.token_input, self.delete_token_btn], style=Pack(direction=ROW, margin=5, align_items="center"))
        folder_box = toga.Box(children=[self.folder_input, folder_btn], style=Pack(direction=ROW, margin=5))
        
        box = toga.Box(
            children=[
                token_box,
                folder_box,
                self.start_stop_btn,
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

    async def delete_token(self, widget):
        try:
            keyring.delete_password(SERVICE_ID, ACCOUNT_ID)
            self.token_input.value = ""
            await self.main_window.dialog(toga.InfoDialog("Success", "Token removed from keyring."))
        except keyring.errors.PasswordDeleteError:
             await self.main_window.dialog(toga.ErrorDialog("Error", "No saved token found to delete."))
        except Exception as e:
            await self.main_window.dialog(toga.ErrorDialog("Error", f"Failed to delete token: {e}"))

    async def toggle_sync(self, widget):
        if self.is_syncing:
            self.stop_requested = True
            self.start_stop_btn.text = "Stopping..."
            self.start_stop_btn.enabled = False # Prevent double clicks
            return

        # START SYNC
        token = self.token_input.value
        folder = self.folder_input.value
        
        if not token:
            await self.main_window.dialog(toga.ErrorDialog("Error", "Please enter an Auth Token."))
            return
            
        # Save token only if not from Env (simple check: if matches env, don't save, else save)
        env_token = os.environ.get("GO_PRO_AUTH_TOKEN")
        if token != env_token:
            try:
                keyring.set_password(SERVICE_ID, ACCOUNT_ID, token)
            except Exception as e:
                print(f"Keyring error: {e}")
            
        self.is_syncing = True
        self.stop_requested = False
        self.start_stop_btn.text = "Stop Sync"
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
            
        def check_cancelled():
            return self.stop_requested

        # Run sync
        try:
            sync_account(token, folder, callback=update_ui, is_cancelled=check_cancelled)
        finally:
            self.reset_ui_state()
    
    def reset_ui_state(self):
        def _reset():
            self.is_syncing = False
            self.stop_requested = False
            self.start_stop_btn.text = "Start Sync"
            self.start_stop_btn.enabled = True
            
            if self.progress_bar.value < 100:
                 self.status_label.text = "Stopped/Finished"

        self.app.loop.call_soon_threadsafe(_reset)

    def update_status(self, msg, progress):
        pass # redundant now
def main():
    return GoProSyncApp("GoPro Cloud Sync", "com.gopro.cloudsync")

if __name__ == '__main__':
    main().main_loop()
