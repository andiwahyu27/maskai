"""MASKAI — Pending transaction state"""
import logging
log = logging.getLogger("maskai.state.pending")

class PendingStore:
    """In-memory pending transactions, keyed by (chat_id, user_id)"""
    def __init__(self):
        self._store = {}
    
    def get(self, chat_id, user_id):
        return self._store.get((chat_id, user_id))
    
    def set(self, chat_id, user_id, value):
        self._store[(chat_id, user_id)] = value
    
    def pop(self, chat_id, user_id):
        return self._store.pop((chat_id, user_id), None)
    
    def __contains__(self, key):
        return key in self._store

# Global singleton
pending = PendingStore()
