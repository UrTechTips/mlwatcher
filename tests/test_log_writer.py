import os
import time
import unittest
from mlwatcher.logger import Logger
from mlwatcher.log_file import log_to_file

LOG_PATH = "../storage/test_log.bin"

class TestLogWriter(unittest.TestCase):
    def setUp(self):
        self.logger = Logger(log_path=LOG_PATH)
        self.logger.start()

    def test_entries(self):
        for i in range(15):
            time.sleep(5)
            log_to_file(LOG_PATH, f'Test message {i}')
    
    def tearDown(self):
        self.logger.stop()

if __name__ == '__main__':
    unittest.main()