def won(x):
    return f"{x:,.0f}"


def pct(part, whole):
    return f"{(part / whole * 100) if whole else 0:.1f}%"
