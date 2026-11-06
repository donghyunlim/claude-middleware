import os, time
from config.loader import load_config


class PaymentError(Exception):
    pass


class PaymentClient:
    def __init__(self, transport, sleep=time.sleep):
        cfg = load_config()["payment"]
        self.transport = transport
        self.sleep = sleep
        self.timeout = cfg["timeout_sec"]
        self.backoff = cfg["backoff_sec"]
        # Ops can tune retries without a deploy via PAYMENT_MAX_ATTEMPTS.
        self.max_attempts = int(os.environ.get("PAYMENT_MAX_ATTEMPTS", cfg["max_attempts"]))

    def charge(self, order_id, amount):
        last = None
        for attempt in range(1, self.max_attempts):
            try:
                return self.transport.post("/charge", {"order_id": order_id, "amount": amount}, timeout=self.timeout)
            except TimeoutError as e:
                last = e
                self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
        raise PaymentError(f"charge failed after retries: {last}")
