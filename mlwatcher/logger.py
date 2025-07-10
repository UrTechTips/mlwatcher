import os
import time
import requests
from threading import Thread, Lock
from mlwatcher.log_reader import LogReader
from mlwatcher.log_file import log_to_file
from mlwatcher.server import Server

PORT = int(os.environ.get('MLWATCH_PORT', '5000'))

class Logger:
    def __init__(self, log_path, poll_interval=15.0, dashboard_url: str=None, verbose=False):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.poll_interval = poll_interval
        self.dashboard_url = dashboard_url
        self.verbose = verbose
        self.entries = []
        self.entries_lock = Lock()

        self.reader = LogReader(log_path, poll_interval=poll_interval)

        if dashboard_url:
            try:
                response = requests.get(f"{dashboard_url}/")
                if response.status_code != 200:
                    raise ValueError(f"Dashboard URL {dashboard_url} is not reachable. Status code: {response.status_code}")
                print(f"Connected to dashboard at {dashboard_url}")
            except requests.RequestException as e:
                raise ValueError(f"Failed to connect to dashboard URL {dashboard_url}: {e}")

        if not self.dashboard_url:
            self.server = Server(port=PORT, verbose=verbose)
            self.server.entries = self.entries

        self.running = True

    def _log_watcher_thread(self) -> None:
        with self.reader as reader:
            while self.running:
                for ts, msg in reader.watch():
                    with self.entries_lock:
                        self.entries.append({'timestamp': ts, 'message': msg})
                    
    def _post_logs_thread(self) -> None:
        while self.running:
            if self.dashboard_url:
                try:
                    with self.entries_lock:
                        logs_to_send = self.entries.copy()
                        self.entries.clear()
                    if logs_to_send:
                        response = requests.post(f"{self.dashboard_url}/post_logs", json={
                            'log': logs_to_send
                        })
                        if response.status_code != 201:
                            print(f"Failed to post logs: {response.status_code} {response.text}")
                        else:
                            if self.verbose:
                                print(f"Logs posted successfully: {len(logs_to_send)} entries")
                except requests.RequestException as e:
                    print(f"Error posting logs: {e}")
            time.sleep(self.poll_interval)

    def start(self) -> None:
        if self.dashboard_url:
            self.post_thread = Thread(target=self._post_logs_thread, daemon=True)
            self.post_thread.start()
        else:
            self.server.start()
        self.watcher_thread = Thread(target=self._log_watcher_thread, daemon=True)
        self.watcher_thread.start()

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
        log_to_file(self.log_path, message)
    
    def stop(self, generate_text: bool = False) -> None:
        self.running = False
        if hasattr(self, 'watcher_thread'):
            self.watcher_thread.join()
        if hasattr(self, 'post_thread'):
            self.post_thread.join()

        if generate_text:
            self.to_text(target_path=self.log_path.replace('.log', '.txt'))

    def to_text(self, target_path: str=None) -> str:
        text = self.reader.to_text()
        if target_path:
            with open(target_path, 'w') as f:
                f.write(text)
        return text

    def __del__(self) -> None:
        self.stop()
        if os.path.exists(self.log_path):
            os.remove(self.log_path)