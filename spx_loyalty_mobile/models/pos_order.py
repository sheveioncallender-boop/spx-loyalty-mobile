"""Receipt/display metadata for orders submitted by this app.

Payment creation, settlement, tax calculation and loyalty stay in native Odoo.
"""
import secrets
import string

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _spx_new_ticket_code(self):
        # Same five-character base-36 format as native POS random5Chars().
        return ''.join(secrets.choice(string.digits + string.ascii_lowercase) for _ in range(5))

    def _spx_repair_app_order_metadata(self):
        """Idempotently refresh only app-originated receipt/display fields."""
        app_orders = self.env['spx.mobile.submission'].sudo().search([
            ('order_id', 'in', self.ids),
        ]).mapped('order_id')
        for order in self & app_orders:
            values = {}
            difference = order.amount_paid - order.amount_total
            if order.currency_id.compare_amounts(order.amount_difference, difference):
                # Identical to native _compute_prices(), without repricing a bill.
                values['amount_difference'] = difference
            if not order.ticket_code:
                values['ticket_code'] = self._spx_new_ticket_code()
            if values:
                order.write(values)

    def add_payment(self, data):
        result = super().add_payment(data)
        # Native add_payment updates amount_paid but leaves this stored display
        # value unchanged. App drafts initially have a negative difference.
        self._spx_repair_app_order_metadata()
        return result
