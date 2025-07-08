import struct
import time
import os

# Record Header Format:
#  - magic:    4 bytes (ASCII 'MLWG')
#  - version:  1 byte (uint8)
#  - timestamp:8 bytes (float64, epoch seconds)
#  - length:   4 bytes (uint32, payload length in bytes)
# Total header size = 4 + 1 + 8 + 4 = 17 bytes
# Payload: UTF-8 encoded log message or MessagePack blob

MAGIC = b'MLWG'
VERSION = 1
HEADER_FMT = '>4sB d I'  # big-endian: magic (4s), version (B), timestamp (d), length (I)
HEADER_SIZE = struct.calcsize(HEADER_FMT)


def log_to_file(log_path: str, message: str):
    payload = message.encode('utf-8')
    ts = time.time()
    header = struct.pack(HEADER_FMT, MAGIC, VERSION, ts, len(payload))
    print(os.path.dirname(log_path))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, 'ab') as f:
        f.write(header)
        f.write(payload)

