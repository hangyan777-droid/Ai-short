"""Conservative CAD quotes. Reservations are enforced transactionally by Store."""
from decimal import Decimal, ROUND_UP

CAP = Decimal('18.00')

def quote_cad(usd, rate='1.40', margin='0.15'):
    values = [Decimal(str(v)) for v in (usd, rate, margin)]
    if any(not v.is_finite() for v in values) or values[0] < 0 or values[1] <= 0 or values[2] < 0:
        raise ValueError('Invalid price, exchange rate or tax margin')
    return (values[0] * values[1] * (1 + values[2])).quantize(Decimal('.01'), rounding=ROUND_UP)
