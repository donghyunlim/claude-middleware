from .io_utils import read_rows


class Product:
    def __init__(self, sku, name, category, unit_price, currency):
        self.sku = sku
        self.name = name
        self.category = category
        self.unit_price = unit_price
        self.currency = currency


def get_product(data_dir, sku):
    for row in read_rows(data_dir, "products.csv"):
        if row["sku"] == sku:
            return Product(row["sku"], row["name"], row["category"], float(row["unit_price"]), row["currency"])
    raise KeyError(sku)
