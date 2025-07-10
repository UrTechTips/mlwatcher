import os
import logging
import socket
from threading import Thread
from flask import Flask, jsonify, render_template, request

class Server:
    def __init__(self, port: int, verbose: bool = False):
        self.PORT = port if port else int(os.environ.get('MLWATCH_PORT', '5000'))
        self.app = Flask(__name__)
        self.entries = []
        self.verbose = verbose
        self._register_routes()

        print("Starting MLWatcher server on port", self.PORT)
        # Print the url
        print(f"Dashboard URL: http://localhost:{self.PORT}")
        print(f"LAN URL: http://{self._get_local_ip()}:{self.PORT}")

        if not self.verbose:
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
            self.app.logger.disabled = True

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except Exception as e:
            print(f"Error getting local IP: {e}")
            local_ip = '127.0.0.1'
        finally:
            s.close()
        return local_ip

    def _register_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html', poll_interval=15*1000)

        @self.app.route('/post_logs', methods=['POST'])
        def post_logs():
            log_entry = request.json.get('log')
            if log_entry:
                self.entries.extend(log_entry)
            return jsonify({'status': 'success'}), 201

        @self.app.route('/logs')
        def get_logs():
            return jsonify(self.entries)

    def _flask_thread(self):
        self.app.run(host="0.0.0.0", port=self.PORT) 
    
    def start(self, block=False):
        if block:
            try:
                self.app.run(host="0.0.0.0", port=self.PORT)
            except KeyboardInterrupt:
                print("\n[MLWatcher] Server stopped by user.")
        else:
            self.flask_thread = Thread(target=self._flask_thread, daemon=True)
            self.flask_thread.start()

    def stop(self):
        if self.flask_thread.is_alive():
            print("Stopping MLWatcher Server...")
            self.flask_thread.join(timeout=1)
            print("MLWatcher Server stopped.")
        else:
            print("MLWatcher Server is not running.")

if __name__ == "__main__":
    server = Server(port=5000, verbose=True)
    server.start(block=True)