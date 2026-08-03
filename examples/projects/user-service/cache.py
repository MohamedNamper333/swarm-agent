"""In-memory cache layer with TTL support."""

import time
import threading


class Cache:
    def __init__(self, default_ttl=300):
        self.default_ttl = default_ttl
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._store:
                entry = self._store[key]
                if time.time() < entry["expires"]:
                    entry["hits"] += 1
                    return entry["value"]
                else:
                    del self._store[key]
        return None

    def set(self, key, value, ttl=None):
        with self._lock:
            self._store[key] = {
                "value": value,
                "expires": time.time() + (ttl or self.default_ttl),
                "hits": 0,
                "created": time.time()
            }

    def delete(self, key):
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self):
        with self._lock:
            total_hits = sum(e["hits"] for e in self._store.values())
            return {
                "entries": len(self._store),
                "total_hits": total_hits,
                "keys": list(self._store.keys())
            }

    def invalidate_pattern(self, prefix):
        with self._lock:
            to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in to_delete:
                del self._store[k]
            return len(to_delete)
