"""Product catalog. Some products are sold and returned by the box."""

PRODUCTS = {
    "CUP-01": {"name": "머그컵", "pack_size": 1},
    "TISSUE-BOX": {"name": "티슈 박스", "pack_size": 24},
    "pen-03": {"name": "볼펜", "pack_size": 12},
}


def normalize_sku(sku):
    return sku.strip().upper()


def pack_size(sku):
    return PRODUCTS[normalize_sku(sku) if normalize_sku(sku) in PRODUCTS else sku]["pack_size"]
