"""Customer returns are recorded in the unit the customer bought (boxes for boxed goods)."""
from .catalog import pack_size


def receive_return(service, sku, boxes):
    """Put returned boxes back into stock."""
    have = service.available(sku)
    service._write(sku, have + boxes)
    return have + boxes
