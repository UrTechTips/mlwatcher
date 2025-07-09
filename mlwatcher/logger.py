import os
import time
import logging
import requests
from threading import Thread, Lock
from mlwatcher.log_reader import LogReader
from flask import Flask, jsonify, render_template
from mlwatcher.log_file import log_to_file

PORT = int(os.environ.get('MLWATCH_PORT', '5000'))

class Logger:
    def __init__(self, log_path, poll_interval=15.0, dashboard_url=None):
        self.log_path = log_path
        self.poll_interval = poll_interval
        self.dashboard_url = dashboard_url

        if not self.dashboard_url:
            self.app = Flask(__name__)
            self.app.logger.setLevel(logging.ERROR)

        self.entries = []
        self.entries_lock = Lock()
        self.running = True
        if not self.dashboard_url:
            self._register_routes()

    def _log_watcher_thread(self):
        with LogReader(self.log_path, poll_interval=self.poll_interval) as reader:
            while self.running:
                for ts, msg in reader.watch():
                    with self.entries_lock:
                        self.entries.append({'timestamp': ts, 'message': msg})
                    
    def _post_logs_thread(self):
        while self.running:
            if self.dashboard_url:
                try:
                    with self.entries_lock:
                        logs_to_send = self.entries.copy()
                        self.entries.clear()
                    if logs_to_send:
                        response = requests.post(self.dashboard_url, json=logs_to_send)
                        if response.status_code != 201:
                            print(f"Failed to post logs: {response.status_code} {response.text}")
                        else:
                            print(f"Logs posted successfully: {len(logs_to_send)} entries")
                except requests.RequestException as e:
                    print(f"Error posting logs: {e}")
            time.sleep(self.poll_interval)


    def _flask_thread(self):
        self.app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

    def _register_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html', poll_interval=self.poll_interval*1000)

        @self.app.route('/logs')
        def get_logs():
            with self.entries_lock:
                new_logs = self.entries.copy()
                self.entries.clear()
            return jsonify(new_logs)

    def start(self):
        if self.dashboard_url:
            self.post_thread = Thread(target=self._post_logs_thread, daemon=True)
            self.post_thread.start()
        else:
            self.flask_thread = Thread(target=self._flask_thread, daemon=True)
            self.flask_thread.start()
        self.watcher_thread = Thread(target=self._log_watcher_thread, daemon=True)
        self.watcher_thread.start()

    def log(self, message):
        print("Logging message:", message)
        log_to_file(self.log_path, message)
    
    def stop(self):
        self.running = False
        if hasattr(self, 'watcher_thread'):
            self.watcher_thread.join()
        if hasattr(self, 'post_thread'):
            self.post_thread.join()