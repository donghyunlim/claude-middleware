"""Stock service: reads go through the cache, writes go to the repo."""
from .cache import Cache, stock_key
from .catalog import normalize_sku


class StockService:
    def __init__(self, repo, cache=None):
        self.repo = repo
        self.cache = cache or Cache()

    def available(self, sku):
        key = stock_key(sku)
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        qty = self.repo.get(sku)
        self.cache.set(key, qty)
        return qty

    def _write(self, sku, qty):
        self.repo.set(sku, qty)
        self.cache.delete(stock_key(normalize_sku(sku)))
