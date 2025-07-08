import os
from threading import Thread
from flask import Flask, jsonify, render_template, request

class Server:
    def __init__(self, port):
        self.PORT = port if port else int(os.environ.get('MLWATCH_PORT', '5000'))
        self.app = Flask(__name__)
        self.entries = []
        self._register_routes()

    def _register_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html', poll_interval=15*1000)

        # Post Route to get logs from calling from server
        @self.app.route('/post_logs', methods=['POST'])
        def post_logs():
            log_entry = request.json.get('log')
            if log_entry:
                self.entries.append(log_entry)
            return jsonify({'status': 'success'}), 201

        @self.app.route('/logs')
        def get_logs():
            return jsonify(self.entries)

    def _flask_thread(self):
        self.app.run(host="0.0.0.0", port=self.PORT) 
    
    def start(self):
        self.flask_thread = Thread(target=self._flask_thread, daemon=True)
        self.flask_thread.start()