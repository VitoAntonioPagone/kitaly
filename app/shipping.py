"""Kitaly's tracked delivery tariff. Amounts are in GBP minor units."""
from dataclasses import dataclass


# Royal Mail Europe Zones 1–3. Availability is controlled separately by the
# merchant's destination allowlist.
EUROPE = frozenset('AD AL AM AT AZ BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GE GI GL GR HR HU IE IS IT KG KZ LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM TJ TM TR UA UZ VA XK'.split())
UK_FREE_SUBTOTAL = 7500
UK_RATE = 450
INTERNATIONAL = {
    'europe': (1000, 2500, 5, 7, 'Europe (excluding Germany)', 'Europa (esclusa la Germania)'),
    'DE': (2000, 2500, 5, 7, 'Germany', 'Germania'),
    'US': (2000, 3000, 7, 10, 'United States', 'Stati Uniti'),
    'world': (1500, 3000, 7, 10, 'Rest of World', 'Resto del mondo'),
}


@dataclass(frozen=True)
class DeliveryRate:
    amount: int
    days: tuple
    service: str


def delivery_rate(country, subtotal, weight_grams):
    if country == 'GB':
        return DeliveryRate(0 if subtotal >= UK_FREE_SUBTOTAL else UK_RATE, (2, 3), 'Royal Mail Tracked 48')
    if weight_grams is None or weight_grams <= 0:
        return None
    zone = country if country in {'DE', 'US'} else 'europe' if country in EUROPE else 'world'
    light, heavy, minimum, maximum, *_ = INTERNATIONAL[zone]
    return DeliveryRate(light if weight_grams < 1000 else heavy, (minimum, maximum), 'Royal Mail International Tracked')
