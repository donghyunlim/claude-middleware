"""Tiny in-process cache shared by the service layer."""
import time


class Cache:
    def __init__(self, ttl=300, clock=time.monotonic):
        self.ttl, self.clock, self._d = ttl, clock, {}

    def get(self, key):
        v = self._d.get(key)
        if not v or v[1] < self.clock():
            return None
        return v[0]

    def set(self, key, value):
        self._d[key] = (value, self.clock() + self.ttl)

    def delete(self, key):
        self._d.pop(key, None)


def stock_key(sku):
    return f"stock:{sku}"
