"""MASKAI — Offset persistence"""
import os, logging
log = logging.getLogger("maskai.utils.offset")

class OffsetStore:
    """Atomic offset file persistence"""
    def __init__(self, path):
        self.path = path
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except PermissionError:
            self.path = "/tmp/maskai_offset.txt"
    
    def load(self):
        if not os.path.exists(self.path):
            return 0
        try:
            content = open(self.path).read().strip()
            return int(content) if content else 0
        except (ValueError, OSError):
            log.warning("Corrupt offset file, resetting to 0")
            return 0
    
    def save(self, offset):
        try:
            with open(self.path + ".tmp", "w") as f:
                f.write(str(offset))
            os.rename(self.path + ".tmp", self.path)
        except OSError as e:
            log.error("Failed to write offset: %s", e)
