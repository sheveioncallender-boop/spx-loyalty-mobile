"""A scoped handoff to Odoo's existing checkout, never a payment implementation."""
from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal
from odoo.addons.spx_loyalty_mobile.controllers.dine_in import DineInAPI
from odoo.addons.spx_loyalty_mobile.controllers.validation import positive_id


class MobilePOSCheckout(DineInAPI):
    def _payment_offer(self, order):
        # A positive next amount is prepared by the cashier's native Validate
        # flow. A received app order alone must not start payment or skip staff.
        if order.state != 'draft' or order.session_id.state != 'opened':
            return None
        amount = order._get_checked_next_online_payment_amount()
        if not amount or order.currency_id.compare_amounts(amount, 0) <= 0:
            return None
        method = order.online_payment_method_id
        if not method:
            return None
        providers = PaymentPortal()._get_allowed_providers_sudo(order, order.partner_id.id, amount)
        providers = providers.filtered(lambda p: p.state in ('test', 'enabled') and p.is_published)
        if not providers:
            return None
        return {'amount': amount, 'currency': order.currency_id.name}

    def _order_data(self, order):
        return {**super()._order_data(order), 'payment_offer': self._payment_offer(order)}

    @http.route()
    def dine_orders(self):
        return super().dine_orders()

    @http.route('/spx/mobile/v2/dine-in/payment', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_payment(self, order_id):
        website, partner = self._scope()
        config = self._config(website, required=True)
        try:
            order_id = positive_id(order_id)
        except ValueError as error:
            raise AccessError(_('This bill is unavailable.')) from error
        # Never trust a submission's old foreign key after a table merge, or a
        # customer-supplied partner, config, amount, currency or checkout URL.
        order = request.env['pos.order'].sudo().search([
            ('id', '=', order_id), ('partner_id', '=', partner.id),
            ('company_id', '=', website.company_id.id), ('config_id', '=', config.id),
        ], limit=1)
        if not order:
            raise AccessError(_('This bill is unavailable.'))
        offer = self._payment_offer(order)
        if not offer:
            raise UserError(_('This bill is not ready for online payment. Please check with our team.'))
        # Token issuance is native. All transaction creation, amount validation,
        # bank verification, payments and accounting remain in pos_online_payment.
        token = order._portal_ensure_token()
        return {**offer, 'order_id': order.id,
                'path': PaymentPortal._get_pay_route(order.id, token)}
