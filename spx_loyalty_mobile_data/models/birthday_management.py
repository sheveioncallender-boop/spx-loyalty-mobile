"""Passive customer app fields and tables; no business overrides or jobs."""
from uuid import uuid4
from odoo import fields, models


class BirthdayAward(models.Model):
    _inherit = 'spx.mobile.birthday.award'

    reason = fields.Char(readonly=True)
