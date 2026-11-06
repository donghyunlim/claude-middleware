"""Invoice line formatting. Used by the PDF renderer and the CSV export."""


def format_krw(amount):
    if amount is None:
        return "-"
    negative = amount < 0
    value = abs(amount)
    value = int(value)
    text = "{:,}".format(value)
    text = text + "원"
    if negative:
        text = "-" + text
    return text


def format_usd(amount):
    if amount is None:
        return "-"
    negative = amount < 0
    value = abs(amount)
    value = round(value, 2)
    text = "{:,.2f}".format(value)
    text = "$" + text
    if negative:
        text = "(" + text + ")"
    return text


def format_jpy(amount):
    if amount is None:
        return "-"
    negative = amount < 0
    value = abs(amount)
    value = round(value)
    text = "{:,}".format(value)
    text = "¥" + text
    if negative:
        text = "-" + text
    return text


def format_line(item, currency):
    if currency == "KRW":
        price = format_krw(item.get("price"))
        total = format_krw(item.get("price") * item.get("qty", 1) if item.get("price") is not None else None)
    elif currency == "USD":
        price = format_usd(item.get("price"))
        total = format_usd(item.get("price") * item.get("qty", 1) if item.get("price") is not None else None)
    elif currency == "JPY":
        price = format_jpy(item.get("price"))
        total = format_jpy(item.get("price") * item.get("qty", 1) if item.get("price") is not None else None)
    else:
        raise ValueError("unsupported currency: " + str(currency))
    name = item.get("name", "")
    if len(name) > 20:
        name = name[:19] + "…"
    return "{:<20} {:>3} x {:>14} = {:>14}".format(name, item.get("qty", 1), price, total)
