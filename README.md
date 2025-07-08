# MLWatcher 📡

A lightweight, zero-cloud, zero-bloat log monitoring tool for ML/DL/RL training runs.  
View your training logs from your **local browser** or send them to a **remote dashboard** over your network — in real time.

---

## 🔧 Features

- 📜 Custom binary log format for fast & efficient writes
- 🔁 Background log polling every N seconds
- 🌐 Local Flask server for viewing logs in the browser
- 🚀 Remote dashboard support via POST requests
- 🧠 Thread-safe, minimal, works on low-spec laptops

---

## 🧪 Installation (Dev Mode)

```bash
git clone https://github.com/yourusername/mlwatcher.git
cd mlwatcher
pip install -e .
```

## 🚀 Usage
Local Mode (Flask UI on same machine)
```python
from mlwatcher import Logger

logger = Logger("logs/train_log.bin")
logger.start()

# during training
logger.log("Epoch 1 - Accuracy: 92.3%")
logger.log("Epoch 2 - Accuracy: 93.1%")
```
Access the dashboard: http://localhost:5000
---

Remote Mode (send logs to another device)
```python
logger = Logger("logs/train_log.bin", dashboard_url="http://192.168.1.20:5000/post_logs")
logger.start()
```
In this case, no local UI is hosted — logs are sent to a remote machine with Flask dashboard.
---
## 📂 Folder Structure
```arduino
mlwatcher/
├── mlwatcher/
│   ├── __init__.py
│   ├── logger.py
│   ├── log_file.py
│   ├── log_reader.py
│   └── templates/
│       └── index.html
├── README.md
├── pyproject.toml
├── setup.cfg
└── .gitignore
```
---

## 📌 Roadmap
- CLI interface (mlwatcher --log-path ...)
- Log filtering by tags (e.g. loss, accuracy, etc.)
- Log persistence in JSON/CSV format
- PyPI release

## ⚖️ License
MIT License. Use it freely. Star it if it helps you ⭐