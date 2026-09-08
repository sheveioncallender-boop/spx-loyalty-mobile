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
