def low_stock(service, skus, threshold=10):
    return [s for s in skus if service.available(s) < threshold]
