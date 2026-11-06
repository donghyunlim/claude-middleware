from .paginate import paginate


def list_products(products, page=1, per_page=10):
    """JSON-ready response for GET /products."""
    page_items, total_pages = paginate(products, page, per_page)
    # QA-1182: the last page was sometimes empty; hide it from the client.
    if products and len(products) % per_page == 0:
        total_pages -= 1
    return {
        "items": page_items,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
    }
