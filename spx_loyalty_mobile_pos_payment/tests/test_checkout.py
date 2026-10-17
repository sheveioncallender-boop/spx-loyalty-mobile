from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.addons.spx_loyalty_mobile.tests.test_dine_in import TestDineInNative
from odoo.addons.spx_loyalty_mobile_pos_payment.controllers.checkout import MobilePOSCheckout


@tagged('post_install', '-at_install')
class TestMobilePOSCheckout(TestDineInNative):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api = MobilePOSCheckout()
        # The shared fixture opens POS for ordering tests. Close its empty
        # session through Odoo before configuring the online payment method.
        cls.config.current_session_id.action_pos_session_closing_control()
        cls.provider = cls.env['payment.provider'].create({
            'name': 'Disposable checkout provider', 'code': 'none', 'state': 'test',
            'is_published': True, 'company_id': cls.config.company_id.id,
            'payment_method_ids': [Command.set(cls.env.ref('payment.payment_method_unknown').ids)],
        })
        cls.online_method = cls.env['pos.payment.method'].create({
            'name': 'Disposable online checkout', 'is_online_payment': True,
            'company_id': cls.config.company_id.id,
            'online_payment_provider_ids': [Command.set(cls.provider.ids)],
        })
        cls.config.payment_method_ids += cls.online_method
        cls.config.open_ui()
        if cls.config.current_session_id.state == 'opening_control':
            cls.config.current_session_id.set_opening_control(0, 'Disposable checkout tests')

    @contextmanager
    def as_customer(self, user=None):
        with super().as_customer(user):
            from odoo.addons.spx_loyalty_mobile.controllers import dine_in
            with patch('odoo.addons.spx_loyalty_mobile_pos_payment.controllers.checkout.request', dine_in.request), \
                 patch('odoo.addons.pos_online_payment.controllers.payment_portal.request', dine_in.request):
                yield

    def make_order(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            receipt = self.api.dine_submit(cart['basket_key'], cart['quote'])['order']
        return self.env['pos.order'].search([('pos_reference', '=', receipt['name'])])

    def test_handoff_requires_cashier_and_creates_no_financial_records(self):
        order = self.make_order()
        with self.as_customer():
            self.assertIsNone(self.api.dine_orders()[0]['payment_offer'])
            with self.assertRaises(UserError):
                self.api.dine_payment(order.id)
        order.get_and_set_online_payments_data(100.0)
        models = ['pos.order', 'pos.payment', 'payment.transaction', 'account.payment', 'account.move', 'loyalty.history']
        before = {model: self.env[model].search_count([]) for model in models}
        with self.as_customer():
            history = self.api.dine_orders()[0]
            self.assertEqual(history['payment_offer']['amount'], 100)
            self.assertNotIn('access_token', str(history))
            result = self.api.dine_payment(order.id)
            repeated = self.api.dine_payment(order.id)
        self.assertEqual(result, repeated)
        self.assertEqual(urlsplit(result['path']).path, f'/pos/pay/{order.id}')
        self.assertEqual(parse_qs(urlsplit(result['path']).query)['access_token'], [order.access_token])
        self.assertEqual(order.state, 'draft')
        self.assertFalse(order.payment_ids)
        self.assertEqual(before, {model: self.env[model].search_count([]) for model in models})

    def test_no_access_to_other_customer_or_reassigned_bill(self):
        order = self.make_order()
        order.get_and_set_online_payments_data(100.0)
        with self.as_customer(self.bob), self.assertRaises(AccessError):
            self.api.dine_payment(order.id)
        order.partner_id = self.bob.partner_id
        with self.as_customer(), self.assertRaises(AccessError):
            self.api.dine_payment(order.id)

    def test_paid_cancelled_closed_and_withdrawn_offers_are_rejected(self):
        order = self.make_order()
        order.get_and_set_online_payments_data(100.0)
        for state in ['paid', 'done', 'cancel']:
            order.state = state
            with self.as_customer(), self.assertRaises(UserError):
                self.api.dine_payment(order.id)
        order.state = 'draft'
        order.session_id.state = 'closing_control'
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_payment(order.id)
        order.session_id.state = 'opened'
        order.get_and_set_online_payments_data(0)
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_payment(order.id)

    def test_partial_amount_is_native_and_unpublished_provider_is_unavailable(self):
        order = self.make_order()
        order.get_and_set_online_payments_data(30.0)
        with self.as_customer():
            self.assertEqual(self.api.dine_payment(order.id)['amount'], 30)
        self.provider.is_published = False
        with self.as_customer():
            self.assertIsNone(self.api.dine_orders()[0]['payment_offer'])
            with self.assertRaises(UserError):
                self.api.dine_payment(order.id)

    def test_invalid_identifiers_are_rejected(self):
        for value in [True, 0, -1, '1', None]:
            with self.as_customer(), self.assertRaises(AccessError):
                self.api.dine_payment(value)
