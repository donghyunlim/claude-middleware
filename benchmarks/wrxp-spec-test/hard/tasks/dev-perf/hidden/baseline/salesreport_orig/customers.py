from .io_utils import read_rows


def get_customer(data_dir, customer_id):
    cid = customer_id.strip()
    for row in read_rows(data_dir, "customers.csv"):
        if row["customer_id"].strip() == cid:
            return {"id": cid, "name": row["name"], "region": row["region"], "tier": row["tier"]}
    return {"id": cid, "name": "(미등록)", "region": "미상", "tier": "일반"}
