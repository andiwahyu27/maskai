"""Amount validation"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
MAX_AMOUNT = Decimal("1000000000000")
MONEY_QUANT = Decimal("0.01")

def parse_positive_amount(value):
    """Validate using Decimal. Returns (Decimal, None) or (None, error)"""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    if value is None:
        return None, "Jumlah wajib diisi"
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None, "Jumlah tidak valid"
    if not amount.is_finite():
        return None, "Jumlah tidak valid"
    if amount <= 0:
        return None, "Jumlah harus lebih dari 0"
    if amount > Decimal("999999999"):
        return None, "Jumlah terlalu besar"
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return amount, None

