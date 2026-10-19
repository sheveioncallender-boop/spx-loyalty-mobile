from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from types import SimpleNamespace

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
            current = self.api.dine_cart()
            cart = self.api.dine_add(self.product.id, 1, current['basket_key'])
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
        for state in ['paid', 'done', 'cancel']:
            # Independent records: native Odoo correctly forbids reopening or
            # changing a bill after it is paid.
            order = self.make_order()
            order.get_and_set_online_payments_data(100.0)
            order.state = state
            with self.as_customer(), self.assertRaises(UserError):
                self.api.dine_payment(order.id)
        order = self.make_order()
        order.get_and_set_online_payments_data(100.0)
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

    def make_attempt(self, order, state='error', amount=100.0):
        if state == 'authorized':
            # The generic disposable provider has no capture feature by
            # default. Enable it for this fixture so native validation can
            # create the authorized attempt whose handoff we must reject.
            self.provider.support_manual_capture = 'full_only'
        return self.env['payment.transaction'].create({
            'provider_id': self.provider.id,
            'payment_method_id': self.env.ref('payment.payment_method_unknown').id,
            'reference': f'checkout-retry-{order.id}-{state}',
            'amount': amount, 'currency_id': order.currency_id.id,
            'partner_id': order.partner_id.id, 'pos_order_id': order.id,
            'operation': 'online_redirect', 'state': state,
        })

    def test_failed_checkout_survives_closed_pos_request_without_writes(self):
        for state in ('error', 'cancel'):
            order = self.make_order()
            order.get_and_set_online_payments_data(100.0)
            self.make_attempt(order, state)
            order.get_and_set_online_payments_data(0)
            models = ['pos.order', 'pos.payment', 'payment.transaction',
                      'account.payment', 'account.move', 'loyalty.history']
            before = {model: self.env[model].search_count([]) for model in models}
            with self.as_customer():
                self.assertEqual(self.api._order_data(order)['payment_offer']['amount'], 100)
                first = self.api.dine_payment(order.id)
                self.assertEqual(first, self.api.dine_payment(order.id))
            self.assertEqual(urlsplit(first['path']).path, f'/pos/pay/{order.id}')
            self.assertEqual(first['amount'], 100)
            self.assertEqual(order.next_online_payment_amount, 0)
            self.assertEqual(order.state, 'draft')
            self.assertFalse(order.payment_ids)
            self.assertEqual(before, {model: self.env[model].search_count([]) for model in models})

    def test_retry_does_not_replace_newer_in_flight_or_successful_attempt(self):
        for state in ('draft', 'pending', 'authorized', 'done'):
            order = self.make_order()
            self.make_attempt(order)
            self.make_attempt(order, state)
            with self.as_customer(), self.assertRaises(UserError):
                self.api.dine_payment(order.id)

    def test_retry_does_not_expand_partial_amount_or_reassigned_customer(self):
        order = self.make_order()
        tx = self.make_attempt(order, amount=30.0)
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_payment(order.id)
        # A newly prepared split amount takes precedence over old attempts.
        order.get_and_set_online_payments_data(20.0)
        with self.as_customer():
            self.assertEqual(self.api.dine_payment(order.id)['amount'], 20)
        order.get_and_set_online_payments_data(0)
        tx.amount = 100.0
        order.partner_id = self.bob.partner_id
        with self.as_customer(self.bob), self.assertRaises(UserError):
            self.api.dine_payment(order.id)

    def test_retry_still_requires_open_unpaid_order_and_published_provider(self):
        order = self.make_order()
        self.make_attempt(order)
        self.provider.is_published = False
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_payment(order.id)
        self.provider.is_published = True
        order.session_id.state = 'closing_control'
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_payment(order.id)
        order.session_id.state = 'opened'
        for state in ('paid', 'done', 'cancel'):
            another = self.make_order()
            self.make_attempt(another)
            another.state = state
            with self.as_customer(), self.assertRaises(UserError):
                self.api.dine_payment(another.id)

    def test_scotia_receipt_reads_only_verified_exact_payment_relation(self):
        order = self.make_order()
        tx = SimpleNamespace(
            pos_order_id=order, company_id=order.company_id,
            provider_code='spx_paybridge_scotia', state='done',
            _fields={'scotia_response_hash_validated': True},
            scotia_response_hash_validated=True, scotia_card_brand='VISA',
            scotia_card_mask='0083',
        )
        payment = SimpleNamespace(
            card_brand=False, card_no=False, pos_order_id=order,
            company_id=order.company_id,
            online_account_payment_id=SimpleNamespace(payment_transaction_id=tx),
        )
        self.assertEqual(self.api._payment_card_details(payment),
                         {'brand': 'Visa', 'last4': '0083'})
        tx.scotia_response_hash_validated = False
        self.assertIsNone(self.api._payment_card_details(payment))
        tx.scotia_response_hash_validated = True
        tx.pos_order_id = self.env['pos.order']
        self.assertIsNone(self.api._payment_card_details(payment))
        tx.pos_order_id = order
        tx._fields = {}  # A regular Odoo installation without the Scotia addon.
        self.assertIsNone(self.api._payment_card_details(payment))

    def loyalty_fixture(self):
        program = self.env['loyalty.program'].create({
            'name': 'Disposable native POS loyalty', 'program_type': 'loyalty',
            'trigger': 'auto', 'applies_on': 'both', 'pos_ok': True,
            'currency_id': self.config.currency_id.id,
            'company_id': self.config.company_id.id,
            'pos_config_ids': [Command.set(self.config.ids)],
            'rule_ids': [Command.create({'reward_point_amount': 1,
                                        'reward_point_mode': 'money', 'minimum_qty': 1})],
            'reward_ids': [Command.create({'reward_type': 'discount', 'discount': 10,
                                          'discount_mode': 'percent',
                                          'discount_applicability': 'order',
                                          'required_points': 100})],
        })
        card = self.env['loyalty.card'].with_context(action_no_send_mail=True).create({
            'program_id': program.id, 'partner_id': self.alice.partner_id.id, 'points': 25,
        })
        order = self.make_order()
        # The test transaction shares one timestamp. Make the chronological
        # relationship explicit without waiting or changing production rules.
        order.date_order = max(program.write_date, *program.rule_ids.mapped('write_date')) + timedelta(seconds=1)
        coupons = {str(card.id): {'program_id': program.id, 'coupon_id': card.id,
                   'partner_id': order.partner_id.id, 'points': 100,
                   'points_earned': 100, 'points_spent': 0}}
        return order, program, card, coupons

    def pay_native(self, order, amount=100):
        method = self.config.payment_method_ids.filtered(lambda m: not m.is_online_payment)[:1]
        order.add_payment({'pos_order_id': order.id, 'amount': amount,
                           'payment_method_id': method.id})
        if order.currency_id.is_zero(order.get_amount_unpaid()):
            order._process_saved_order(False)

    def test_saved_native_loyalty_survives_cancelled_checkout_and_browser_loss(self):
        order, program, card, coupons = self.loyalty_fixture()
        order.spx_prepare_loyalty(coupons)
        order.get_and_set_online_payments_data(100)
        self.make_attempt(order, 'cancel')
        order.get_and_set_online_payments_data(0)
        self.assertEqual(card.points, 25)
        self.assertTrue(order.spx_loyalty_snapshot)
        with self.assertRaises(UserError):
            order.confirm_coupon_programs(coupons)
        self.pay_native(order, 40)
        self.assertEqual(card.points, 25)
        self.assertEqual(order._spx_finalize_loyalty(), {})
        self.pay_native(order, 60)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(card.points, 125)
        self.assertTrue(order.spx_loyalty_finalized)
        self.assertFalse(order.spx_loyalty_snapshot)
        before = (order.amount_paid, order.payment_ids.ids)
        order._spx_finalize_loyalty()
        result = order.confirm_coupon_programs(coupons)
        self.assertEqual(result['coupon_updates'][0]['points'], 125)
        self.assertEqual(card.points, 125)
        history = card.history_ids.filtered(lambda h: h.order_model == 'pos.order' and h.order_id == order.id)
        self.assertEqual(len(history), 1)
        self.assertEqual((history.issued, history.used), (100, 0))
        self.assertEqual(before, (order.amount_paid, order.payment_ids.ids))

    def test_loyalty_snapshot_rejects_changed_customer_and_bill(self):
        for change in ('customer', 'line'):
            order, program, card, coupons = self.loyalty_fixture()
            order.spx_prepare_loyalty(coupons)
            if change == 'customer':
                order.partner_id = self.bob.partner_id
            else:
                order.lines.discount = 10
            self.pay_native(order, order.get_amount_unpaid())
            self.assertEqual(order.state, 'paid')
            self.assertEqual(card.points, 25)
            self.assertFalse(order.spx_loyalty_finalized)

    def test_customer_cannot_supply_points_or_recover_other_orders(self):
        order, program, card, coupons = self.loyalty_fixture()
        with self.assertRaises(AccessError):
            order.with_user(self.alice).spx_prepare_loyalty(coupons)
        with self.assertRaises(AccessError):
            order.with_user(self.alice).confirm_coupon_programs(coupons)
        with self.assertRaises(AccessError):
            self.env['pos.order'].with_user(self.alice).spx_loyalty_recovery_orders(self.config.id)
        invalid = deepcopy(coupons)
        invalid[str(card.id)]['partner_id'] = self.bob.partner_id.id
        with self.assertRaises(UserError):
            order.spx_prepare_loyalty(invalid)
        self.assertFalse(order.spx_loyalty_snapshot)

    def test_loyalty_failure_does_not_undo_native_payment(self):
        order, program, card, coupons = self.loyalty_fixture()
        order.spx_prepare_loyalty(coupons)
        with patch.object(type(order), 'confirm_coupon_programs', side_effect=UserError('Temporary loyalty failure')):
            with self.assertLogs('odoo.addons.spx_loyalty_mobile_pos_payment.models.pos_order', level='ERROR'):
                self.pay_native(order)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.amount_paid, 100)
        self.assertEqual(len(order.payment_ids), 1)
        self.assertEqual(card.points, 25)
        self.assertTrue(order.spx_loyalty_snapshot)
        self.assertFalse(order.spx_loyalty_finalized)
        order._spx_finalize_loyalty()
        self.assertEqual(card.points, 125)

    def test_old_paid_bill_recovers_once_without_changing_financial_records(self):
        order, program, card, coupons = self.loyalty_fixture()
        self.pay_native(order)
        self.assertEqual(card.points, 25)
        models = ['pos.order', 'pos.payment', 'payment.transaction', 'account.payment', 'account.move']
        before = {model: self.env[model].search_count([]) for model in models}
        self.assertTrue(order.spx_prepare_loyalty(coupons, recovery=True)['prepared'])
        self.assertEqual(card.points, 125)
        self.assertFalse(order.spx_prepare_loyalty(coupons, recovery=True)['prepared'])
        self.assertEqual(before, {model: self.env[model].search_count([]) for model in models})

    def test_native_online_callback_finishes_saved_loyalty_without_pos_browser(self):
        order, program, card, coupons = self.loyalty_fixture()
        order.spx_prepare_loyalty(coupons)
        tx = self.make_attempt(order, 'done')
        journal = self.env['account.journal'].search([
            ('company_id', '=', order.company_id.id), ('type', '=', 'bank'),
        ], limit=1)
        # Native account_payment normally creates this before POS processing.
        # Supply a real posted accounting payment, without an external gateway.
        payment = self.env['account.payment'].create({
            'journal_id': journal.id, 'payment_type': 'inbound',
            'partner_type': 'customer', 'partner_id': order.partner_id.id,
            'amount': 100, 'currency_id': order.currency_id.id,
            'payment_method_line_id': journal.inbound_payment_method_line_ids[:1].id,
            'payment_transaction_id': tx.id,
        })
        payment.action_post()
        tx.payment_id = payment
        tx._process_pos_online_payment()
        self.assertEqual(order.state, 'paid')
        self.assertEqual(card.points, 125)
        self.assertEqual(order.payment_ids.online_account_payment_id, payment)
        tx._process_pos_online_payment()
        self.assertEqual(len(order.payment_ids), 1)
        self.assertEqual(card.points, 125)
        # Discovery loads an older missing handoff through native read_pos_orders.
        legacy, legacy_program, legacy_card, legacy_coupons = self.loyalty_fixture()
        self.pay_native(legacy)
        legacy.payment_ids.online_account_payment_id = payment
        pending = self.env['pos.order'].spx_loyalty_recovery_orders(self.config.id)
        self.assertIn(legacy.id, pending['programs'])
        self.assertNotIn(order.id, pending['programs'])
        self.assertIn(legacy.id, [item['id'] for item in pending['orders']['pos.order']])

    def test_historical_recovery_rejects_changed_rules_and_reward_spending(self):
        order, program, card, coupons = self.loyalty_fixture()
        self.pay_native(order)
        old_date = order.date_order
        order.date_order = program.write_date - timedelta(seconds=1)
        with self.assertRaises(UserError):
            order.spx_prepare_loyalty(coupons, recovery=True)
        order.date_order = old_date
        invalid = deepcopy(coupons)
        invalid[str(card.id)]['points_spent'] = 100
        with self.assertRaises(UserError):
            order.spx_prepare_loyalty(invalid, recovery=True)
        self.assertEqual(card.points, 25)

    def test_non_app_orders_keep_native_loyalty_confirmation(self):
        order, program, card, coupons = self.loyalty_fixture()
        other = order.copy({'state': 'draft', 'payment_ids': []})
        self.assertFalse(other.spx_prepare_loyalty(coupons)['prepared'])
        # Native confirmation has no fully-paid restriction; only app orders
        # gain that guard. Preserve the standard POS RPC for unrelated orders.
        other.confirm_coupon_programs(coupons)
        self.assertEqual(card.points, 125)


