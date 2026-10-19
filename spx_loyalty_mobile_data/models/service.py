"""Passive service preferences, retained with the customer's app basket."""
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    spx_mobile_takeaway_preset_id = fields.Many2one(
        'pos.preset', string='App Takeaway preset', groups='base.group_system',
        ondelete='set null',
        help='Select an existing immediate, non-delivery preset available in the app POS. '
             'Orders arrive unpaid for staff to review, send to preparation and settle.',
    )


class MobileBasket(models.Model):
    _inherit = 'spx.mobile.basket'

    service = fields.Selection(
        [('dine_in', 'Dine-in'), ('takeaway', 'Takeaway')],
        required=True, default='dine_in',
    )
