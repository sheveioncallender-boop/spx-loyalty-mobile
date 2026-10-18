"""A scoped handoff to Odoo's existing checkout, never a payment implementation."""
from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal
from odoo.addons.spx_loyalty_mobile.controllers.dine_in import DineInAPI
from odoo.addons.spx_loyalty_mobile.controllers.validation import positive_id, public_card_details


class MobilePOSCheckout(DineInAPI):
    def _payment_card_details(self, payment):
        details = super()._payment_card_details(payment)
        # Follow the exact native payment relation; never search by customer,
        # amount or a receipt string. Scotia remains an optional installation.
        tx = payment.online_account_payment_id.payment_transaction_id
        if (tx and tx.pos_order_id == payment.pos_order_id
                and tx.company_id == payment.company_id
                and tx.provider_code == 'spx_paybridge_scotia'
                and tx.state in ('authorized', 'done')
                and 'scotia_response_hash_validated' in tx._fields
                and tx.scotia_response_hash_validated):
            bank = public_card_details(tx.scotia_card_brand, tx.scotia_card_mask)
            if bank:
                details = {key: bank.get(key) or (details or {}).get(key, '')
                           for key in ('brand', 'last4')}
        return details

    def _payment_offer(self, order):
        # A positive next amount is prepared by the cashier's native Validate
        # flow. A received app order alone must not start payment or skip staff.
        if order.state != 'draft' or order.session_id.state != 'opened':
            return None
        amount = order._get_checked_next_online_payment_amount()
        if not amount:
            # Closing the POS QR dialog clears its next amount, but Odoo's
            # portal still allows the unpaid balance to be retried. Recover
            # that handoff only after the latest attempt failed, for the same
            # customer, currency and balance. A newly submitted bill must
            # still wait for the cashier; never manufacture a payment request.
            tx = request.env['payment.transaction'].sudo().search([
                ('pos_order_id', '=', order.id),
            ], order='id desc', limit=1)
            if (not tx or tx.state not in ('cancel', 'error')
                    or tx.partner_id != order.partner_id
                    or tx.company_id != order.company_id
                    or tx.currency_id != order.currency_id):
                return None
            amount = PaymentPortal._get_amount_to_pay(order)
            if order.currency_id.compare_amounts(tx.amount, amount) != 0:
                return None
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

    @http.route(type='jsonrpc', auth='user', website=True, methods=['POST'])
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

