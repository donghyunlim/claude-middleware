import datetime as dt
from dataclasses import dataclass


class CustomerNotFound(LookupError):
    pass


@dataclass(frozen=True)
class Customer:
    customer_id: str
    legal_name: str
    display_name: str
    phone_e164: str
    created_at: dt.datetime  # timezone-aware, UTC

    @classmethod
    def from_record(cls, r):
        return cls(customer_id=r["customer_id"], legal_name=r["legal_name"], display_name=r["display_name"],
                   phone_e164=r["phone_e164"],
                   created_at=dt.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")))
