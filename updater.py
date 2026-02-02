import requests
import sys
import os
import platform
import subprocess
from packaging import version
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- CONFIGURATION ---
REPO_OWNER = "cad3n123"
REPO_NAME = "image-processor"
# ---------------------

def get_current_version():
    """Reads version from bundled file or returns dev-build."""
    try:
        # sys._MEIPASS is the temp folder where PyInstaller extracts files
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
        path = os.path.join(base_path, 'version.txt')
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0-dev"

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            data = b""
            downloaded = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    data += chunk
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        self.progress.emit(pct)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class Updater:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.system = platform.system().lower()
        self.current_version = get_current_version()
        
        # Only check for updates if we aren't in dev mode
        if "dev" not in self.current_version:
            self.check_for_updates()

    def check_for_updates(self):
        try:
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200: return

            data = resp.json()
            latest_tag = data.get("tag_name", "0.0.0").lstrip("v")
            curr_ver = self.current_version.lstrip("v")

            if version.parse(latest_tag) > version.parse(curr_ver):
                self.prompt_update(latest_tag, data.get("assets", []))
        except Exception:
            pass 

    def prompt_update(self, new_ver, assets):
        asset_url = self.find_asset_url(assets)
        if not asset_url: return

        reply = QMessageBox.question(
            self.parent, 
            "Update Available", 
            f"New version {new_ver} is available!\n"
            f"Current: {self.current_version}\n\n"
            "Update and restart now?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            self.start_download(asset_url)

    def find_asset_url(self, assets):
        suffix = ""
        if self.system == "windows": suffix = "_win.exe"
        elif self.system == "darwin": suffix = "_mac"
        else: suffix = "_linux"
        
        for asset in assets:
            if asset["name"].endswith(suffix):
                return asset["browser_download_url"]
        return None

    def start_download(self, url):
        self.pd = QProgressDialog("Downloading Update...", "Cancel", 0, 100, self.parent)
        self.pd.setWindowModality(Qt.WindowModality.WindowModal)
        self.pd.setAutoClose(False)
        self.pd.setAutoReset(False)
        self.pd.show()

        self.worker = DownloadWorker(url)
        self.worker.progress.connect(self.pd.setValue)
        self.worker.finished.connect(self.install_and_restart)
        self.worker.error.connect(lambda e: QMessageBox.critical(self.parent, "Error", str(e)))
        self.worker.start()

    def install_and_restart(self, content):
        self.pd.setLabelText("Installing...")
        current_exe = sys.executable
        old_exe = current_exe + ".old"
        
        # Clean up previous old file if it exists
        if os.path.exists(old_exe):
            try: os.remove(old_exe)
            except: pass

        try:
            os.rename(current_exe, old_exe)
            with open(current_exe, 'wb') as f:
                f.write(content)
            
            if self.system != "windows":
                os.chmod(current_exe, 0o755)

            QMessageBox.information(self.parent, "Success", "Restarting...")
            subprocess.Popen([current_exe] + sys.argv[1:])
            sys.exit()
        except Exception as e:
            if os.path.exists(old_exe): os.rename(old_exe, current_exe)
            QMessageBox.critical(self.parent, "Update Error", str(e))
