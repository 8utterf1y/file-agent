def calculate_total(items):
    total = 0
    for item in items:
        price = item.get("price", 0)
        count = item.get("count", 1)
        total += price * count
    if total < 0:
        return 0
    return round(total, 2)

