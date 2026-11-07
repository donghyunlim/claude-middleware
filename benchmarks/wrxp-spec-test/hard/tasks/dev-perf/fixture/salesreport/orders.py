from .io_utils import read_rows


def load_lines(data_dir):
    lines = []
    for row in read_rows(data_dir, "order_lines.csv"):
        lines.append({"order_id": row["order_id"], "date": row["order_date"], "customer_id": row["customer_id"],
                      "sku": row["sku"], "qty": int(row["qty"])})
    return lines
