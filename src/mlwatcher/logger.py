import os
import time
import requests
from threading import Thread, Lock, Event  # Import Event
from mlwatcher.log_reader import LogReader
from mlwatcher.log_file import log_to_file
from mlwatcher.server import Server

PORT = int(os.environ.get('MLWATCH_PORT', '5000'))

class Logger:
    """A Logger class that monitors a log file, serves logs via a web server, and optionally posts logs to a remote dashboard.
    Attributes:
        log_path (str): Path to the log file.
        poll_interval (float): Interval in seconds to poll the log file for new entries.
        dashboard_url (str): URL of the remote dashboard to post logs to. If None, a local server is started.
        verbose (bool): If True, prints log messages to the console.
    Functions:
        start(): Starts the log monitoring and server/posting threads.
        log(message): Logs a message to the log file and optionally prints it to the console.
        stop(generate_text): Stops the logger and optionally generates a text file from the log.
        to_text(target_path): Converts the log file to a text format and saves it to target_path if provided.
    Example:
        logger = Logger(log_path='training.log', poll_interval=10.0, dashboard_url='http://localhost:8000', verbose=True)
        logger.start()
        logger.log('Training started')
        ...
        logger.stop(generate_text=True)
    """

    def __init__(self, log_path, poll_interval=15.0, dashboard_url: str=None, verbose=False):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.poll_interval = poll_interval
        self.dashboard_url = dashboard_url
        self.verbose = verbose
        self.entries = []
        self.entries_lock = Lock()
        self.stop_event = Event()  # Create a stop event

        self.reader = LogReader(log_path, poll_interval=poll_interval, stop_event=self.stop_event)

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

    def _log_watcher_thread(self) -> None:
        # NOTE: This thread will still block if LogReader.watch() blocks indefinitely.
        # The LogReader class itself should ideally be designed to be non-blocking
        # or accept a timeout or a stop event.
        # However, structuring the loop this way is the correct pattern.
        with self.reader as reader:
            while not self.stop_event.is_set():
                # This call is the critical part. If reader.watch() is a generator
                # that yields items and then waits, it will block here.
                for ts, msg in reader.watch():
                    if self.stop_event.is_set():
                        break # Check the event again to break out of the inner loop
                    with self.entries_lock:
                        self.entries.append({'timestamp': ts, 'message': msg})

    def _post_logs_thread(self) -> None:
        while not self.stop_event.is_set():
            if self.dashboard_url:
                logs_to_send = []
                try:
                    with self.entries_lock:
                        if self.entries:
                            logs_to_send = self.entries.copy()
                            self.entries.clear()

                    if logs_to_send:
                        response = requests.post(f"{self.dashboard_url}/post_logs", json={
                            'log': logs_to_send
                        })
                        if response.status_code != 201:
                            print(f"Failed to post logs: {response.status_code} {response.text}")
                            # If posting fails, consider adding logs back to the main list
                            with self.entries_lock:
                                self.entries.extend(logs_to_send)
                        elif self.verbose:
                            print(f"Logs posted successfully: {len(logs_to_send)} entries")
                except requests.RequestException as e:
                    print(f"Error posting logs: {e}")
            
            # Use the event's wait method instead of time.sleep()
            # This will return immediately if the event is set, making shutdown fast.
            self.stop_event.wait(self.poll_interval)

    def start(self) -> None:
        """Starts the log monitoring and server/posting threads.\n
        If dashboard_url is provided, starts a thread to post logs to the dashboard.\n
        If no dashboard_url is provided, starts a local web server to serve logs.
        """
        if self.dashboard_url:
            self.post_thread = Thread(target=self._post_logs_thread, daemon=True)
            self.post_thread.start()
        else:
            self.server.start()
        self.watcher_thread = Thread(target=self._log_watcher_thread, daemon=True)
        self.watcher_thread.start()

    def log(self, message: str) -> None:
        """Logs a message to the log file and optionally prints it to the console.
        Args:
            message (str): The message to log.
        """
        if self.verbose:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
        log_to_file(self.log_path, message)
    
    def stop(self, generate_text: bool = False) -> None:
        """Stops the logger and optionally generates a text file from the log.
        Args:
            generate_text (bool): If True, generates a text file from the log.
        """
        if not self.stop_event.is_set():
            print("Stopping logger...")
            self.stop_event.set()  # Signal all threads to stop

            # Stop the server if it exists and has a stop method
            if hasattr(self, 'server') and hasattr(self.server, 'stop'):
                self.server.stop()

            # Wait for threads to finish
            if hasattr(self, 'watcher_thread'):
                self.watcher_thread.join(timeout=self.poll_interval + 1) # Add a timeout to join
            if hasattr(self, 'post_thread'):
                self.post_thread.join(timeout=self.poll_interval + 1) # Add a timeout to join

            if generate_text:
                self.to_text(target_path=self.log_path.replace('.log', '.txt'))
            print("Logger stopped.")


    def to_text(self, target_path: str=None) -> str:
        """Converts the log to a text format.

        Args:
            target_path (str, optional): The path to save the text file. Defaults to None.

        Returns:
            str: The log in text format.
        """
        text = self.reader.to_text()
        if target_path:
            with open(target_path, 'w') as f:
                f.write(text)
        return text

    def __del__(self) -> None:
        # __del__ is unreliable, but it's good to have a fallback
        self.stop()
        try:
            if os.path.exists(self.log_path):
                os.remove(self.log_path)
        except (AttributeError, TypeError):
             # This can happen if __init__ failed partway through
            pass