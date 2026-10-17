"""Dependency-free request validation; also exercised outside an Odoo runtime."""
import math
import re


def positive_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError('Invalid record identifier.')
    return value


def quantity(value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Enter a valid quantity.')
    if not math.isfinite(value) or value > 99 or value < (0 if allow_zero else 1):
        raise ValueError('Quantity must be between %s and 99.' % (0 if allow_zero else 1))
    if int(value) != value:
        raise ValueError('Only whole item quantities are supported in the app.')
    return int(value)


def mutation_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9-]{16,64}', value):
        raise ValueError('A valid request identifier is required.')
    return value


def public_card_details(brand, number):
    """Only a known card brand and last four digits may reach a customer."""
    brands = {
        'visa': 'Visa', 'mastercard': 'Mastercard', 'mc': 'Mastercard',
        'amex': 'American Express', 'americanexpress': 'American Express',
        'discover': 'Discover', 'diners': 'Diners Club', 'dinersclub': 'Diners Club',
        'jcb': 'JCB', 'unionpay': 'UnionPay', 'maestro': 'Maestro',
    }
    brand = brands.get(re.sub(r'[^a-z]', '', str(brand or '').lower()), '')
    number = str(number or '').strip()
    digits = re.sub(r'[^0-9]', '', number)
    last4 = digits[-4:] if (len(digits) >= 4 and
                           re.fullmatch(r'[0-9xX*•\s-]+', number)) else ''
    return {'brand': brand, 'last4': last4} if brand or last4 else None
