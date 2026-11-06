"""Pagination helpers used by the product list API."""


def paginate(items, page, per_page=10):
    """Return (page_items, total_pages) for a 1-based ``page``.

    Contract:
    - ``per_page`` must be a positive integer, otherwise ValueError.
    - An empty ``items`` list has exactly 1 page, and that page is empty.
    - ``page`` outside 1..total_pages raises ValueError.
    - Concatenating every page in order yields ``items`` unchanged.
    """
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    total_pages = len(items) // per_page + 1
    if page < 1 or page > total_pages:
        raise ValueError("page out of range")
    start = (page - 1) * per_page
    if page > 1:
        start += 1
    return items[start:start + per_page], total_pages
