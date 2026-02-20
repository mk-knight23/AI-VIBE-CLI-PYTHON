import json
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
SHARED_PATH = Path(os.path.expanduser("~/.vibe/shared_context.json"))

class SharedContext:
    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SharedContext, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self):
        try:
            if SHARED_PATH.exists():
                content = SHARED_PATH.read_text(encoding="utf-8")
                self._data = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load shared context: {e}")

    def save(self):
        try:
            SHARED_PATH.parent.mkdir(parents=True, exist_ok=True)
            SHARED_PATH.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save shared context: {e}")

    def get(self, key, default=None):
        self.load() # Ensure fresh data
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._data['last_updated'] = datetime.utcnow().isoformat()
        self._data['updated_by'] = 'friday-ai'
        self.save()

    def update(self, updates: dict):
        self.load()
        self._data.update(updates)
        self._data['last_updated'] = datetime.utcnow().isoformat()
        self._data['updated_by'] = 'friday-ai'
        self.save()
