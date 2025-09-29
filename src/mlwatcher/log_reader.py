import struct
import os
import time
from threading import Event

MAGIC = b'MLWG'
VERSION = 1
HEADER_FMT = '>4sB d I'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

class LogReader:
    def __init__(self, log_path: str, poll_interval: float = 5.0, stop_event: Event = None):
        self.log_path = log_path
        self.poll_interval = poll_interval
        self.stop_event = stop_event or Event()
        self.offset = 0

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_event.set()

    def _read_new_entries(self):
        entries = []
        if not os.path.exists(self.log_path):
            return entries

        with open(self.log_path, 'rb') as f:
            f.seek(self.offset)
            while True:
                header = f.read(HEADER_SIZE)
                if len(header) < HEADER_SIZE:
                    break

                magic, version, ts, length = struct.unpack(HEADER_FMT, header)
                if magic != MAGIC or version != VERSION:
                    raise ValueError("Log file unsupported or corrupted.")

                payload = f.read(length)
                if len(payload) < length:
                    raise ValueError("Log file corrupted, incomplete payload.")

                message = payload.decode('utf-8', errors='replace')
                entries.append((ts, message))
                self.offset = f.tell()
        return entries

    def watch(self):
        """Generator: yields each new (timestamp, message) as they arrive."""
        while not self.stop_event.is_set():
            new_entries = self._read_new_entries()
            for ts, msg in new_entries:
                yield ts, msg
            self.stop_event.wait(self.poll_interval)

    def to_text(self) -> str:
        if not os.path.exists(self.log_path):
            return ""
        
        with open(self.log_path, 'rb') as f:
            f.seek(0)
            text_entries = []
            while True:
                header = f.read(HEADER_SIZE)
                if len(header) < HEADER_SIZE:
                    break

                magic, version, ts, length = struct.unpack(HEADER_FMT, header)
                if magic != MAGIC or version != VERSION:
                    raise ValueError("Log file unsupported or corrupted.")
                
                payload = f.read(length)
                if len(payload) < length:
                    raise ValueError("Log file corrupted, incomplete payload.")
                message = payload.decode('utf-8', errors='replace')
                text_entries.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} - {message}")
        
            return "\n".join(text_entries)
