"""Native ORM integration checks. Run on a disposable Odoo 19 database."""
from contextlib import contextmanager
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.spx_loyalty_mobile.controllers.dine_in import DineInAPI
from odoo.addons.spx_loyalty_mobile.controllers.validation import public_card_details


@tagged('post_install', '-at_install')
class TestDineInNative(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.config.write({'module_pos_restaurant': True, 'use_presets': False,
                          'use_pricelist': True, 'pricelist_id': cls.currency_pricelist.id,
                          'available_pricelist_ids': [Command.set(cls.currency_pricelist.ids)]})
        cls.config.open_ui()
        if cls.config.current_session_id.state == 'opening_control':
            cls.config.current_session_id.set_opening_control(0, 'Disposable acceptance tests')
        cls.website = cls.env['website'].create({'name': 'Dine-in tests', 'company_id': cls.config.company_id.id,
                                                'spx_mobile_enabled': True, 'spx_mobile_pos_config_id': cls.config.id})
        cls.alice, cls.bob = cls.env['res.users'].with_context(no_reset_password=True).create([
            {'name': name, 'login': login, 'company_id': cls.config.company_id.id,
             'company_ids': [Command.set(cls.config.company_id.ids)],
             'group_ids': [Command.set([cls.env.ref('base.group_portal').id])], 'spx_mobile_legacy_access': True}
            for name, login in [('Dine-in Alice', 'dine-in-alice'), ('Dine-in Bob', 'dine-in-bob')]
        ])
        cls.product = cls.env['product.product'].create({
            'name': 'Published dine-in item', 'type': 'service', 'list_price': 100,
            'sale_ok': True, 'available_in_pos': True, 'is_published': True,
            'website_id': cls.website.id, 'taxes_id': [Command.clear()],
            'property_account_income_id': cls.sales_account.id,
        })
        cls.api = DineInAPI()

    @contextmanager
    def as_customer(self, user=None):
        req = SimpleNamespace(env=self.env(user=(user or self.alice).id), website=self.website)
        with patch('odoo.http.request', req), \
             patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', req), \
             patch('odoo.addons.spx_loyalty_mobile.controllers.dine_in.request', req):
            yield

    def test_quote_and_submit_native_unpaid_order_and_replay(self):
        before = self.env['pos.order'].search_count([])
        cards_before = self.env['loyalty.card'].search_count([])
        history_before = self.env['loyalty.history'].search_count([])
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 2)
            self.assertEqual(self.env['pos.order'].search_count([]), before)
            self.assertEqual(cart['total'], 200)
            result = self.api.dine_submit(cart['basket_key'], cart['quote'])
            self.assertEqual(result['status'], 'received')
            self.assertEqual(self.api.dine_submit(cart['basket_key'], cart['quote']), result)
            self.assertFalse(self.api.dine_cart()['lines'])
        self.assertEqual(self.env['pos.order'].search_count([]), before + 1)
        order = self.env['pos.order'].search([('pos_reference', '=', result['order']['name'])])
        self.assertEqual(order.partner_id, self.alice.partner_id)
        self.assertEqual(order.config_id, self.config)
        self.assertEqual(order.state, 'draft')
        self.assertFalse(order.table_id)
        self.assertFalse(order.payment_ids)
        self.assertFalse(order.picking_ids)
        self.assertEqual(self.env['loyalty.card'].search_count([]), cards_before)
        self.assertEqual(self.env['loyalty.history'].search_count([]), history_before)
        self.assertEqual(order.lines.product_id, self.product)
        self.assertEqual(order.amount_total, cart['total'])
        self.assertRegex(order.ticket_code, r'^[0-9a-z]{5}$')
        tags = json.loads(order.internal_note)
        self.assertIsInstance(tags, list)
        self.assertTrue(all(isinstance(tag.get('text'), str) for tag in tags))
        self.assertTrue(all(isinstance(tag.get('colorIndex'), int) for tag in tags))

    def _submitted_order(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            result = self.api.dine_submit(cart['basket_key'], cart['quote'])
        return self.env['pos.order'].search([('pos_reference', '=', result['order']['name'])])

    def test_native_partial_and_full_payment_refresh_display_difference(self):
        order = self._submitted_order()
        code = order.ticket_code
        method = self.config.payment_method_ids[:1]
        for amount, expected in [(40, -60), (60, 0)]:
            order.add_payment({'pos_order_id': order.id, 'amount': amount,
                               'payment_method_id': method.id})
            self.assertEqual(order.amount_difference, expected)
        order._process_saved_order(False)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.amount_paid, 100)
        self.assertEqual(order.amount_total, 100)
        self.assertEqual(len(order.payment_ids), 2)
        self.assertEqual(order.ticket_code, code)

    def test_upgrade_metadata_repair_is_scoped_and_idempotent(self):
        order = self._submitted_order()
        order.add_payment({'pos_order_id': order.id, 'amount': 100,
                           'payment_method_id': self.config.payment_method_ids[:1].id})
        order._process_saved_order(False)
        order.write({'amount_difference': -100, 'ticket_code': False})
        unrelated = order.copy({'state': 'draft', 'amount_paid': 0,
                                'payment_ids': [], 'ticket_code': False,
                                'amount_difference': -321})
        models = ['pos.payment', 'payment.transaction', 'account.payment', 'account.move', 'loyalty.history']
        before = {model: self.env[model].search_count([]) for model in models}
        (order | unrelated)._spx_repair_app_order_metadata()
        code = order.ticket_code
        (order | unrelated)._spx_repair_app_order_metadata()
        self.assertEqual(order.amount_difference, 0)
        self.assertRegex(code, r'^[0-9a-z]{5}$')
        self.assertEqual(order.ticket_code, code)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.amount_paid, 100)
        self.assertEqual(order.amount_total, 100)
        self.assertFalse(unrelated.ticket_code)
        self.assertEqual(unrelated.amount_difference, -321)
        self.assertEqual(before, {model: self.env[model].search_count([]) for model in models})

    def test_pos_ui_payment_sync_refreshes_difference_and_replay_is_safe(self):
        order = self._submitted_order()
        code = order.ticket_code
        method = self.config.payment_method_ids.filtered('is_cash_count')[:1]
        self.assertTrue(method)
        history_before = self.env['loyalty.history'].search_count([])
        for amount, state, expected in [(40, 'draft', -60), (60, 'paid', 0)]:
            payload = {
                'uuid': order.uuid, 'session_id': order.session_id.id,
                'state': state, 'lines': [], 'amount_return': 0,
                # Reproduce a stale value received from an app-created draft.
                'amount_difference': -100,
                'payment_ids': [Command.create({
                    'uuid': str(uuid4()), 'amount': amount,
                    'payment_method_id': method.id,
                })],
            }
            self.env['pos.order'].sync_from_ui([deepcopy(payload)])
            self.assertEqual(order.amount_difference, expected)
            self.assertEqual(order.state, state)
        self.assertEqual(order.amount_paid, 100)
        self.assertEqual(order.amount_total, 100)
        self.assertEqual(len(order.payment_ids), 2)
        payment_ids = order.payment_ids.ids
        self.env['pos.order'].sync_from_ui([deepcopy(payload)])
        self.assertEqual(order.payment_ids.ids, payment_ids)
        self.assertEqual(order.amount_difference, 0)
        self.assertEqual(order.ticket_code, code)
        self.assertEqual(self.env['loyalty.history'].search_count([]), history_before)

    def test_pos_ui_sync_does_not_repair_unrelated_orders(self):
        order = self._submitted_order().copy({
            'state': 'draft', 'amount_paid': 0, 'payment_ids': [],
            'ticket_code': False, 'amount_difference': -321,
        })
        self.env['pos.order'].sync_from_ui([{
            'uuid': order.uuid, 'session_id': order.session_id.id,
            'state': 'draft', 'lines': [], 'payment_ids': [], 'amount_return': 0,
        }])
        self.assertEqual(order.amount_difference, -321)
        self.assertFalse(order.ticket_code)

    def test_customer_receipt_uses_native_methods_and_masks_card_details(self):
        order = self._submitted_order()
        method = self.config.payment_method_ids[:1]
        order.add_payment({'pos_order_id': order.id, 'amount': 40,
                           'payment_method_id': method.id})
        with self.as_customer():
            self.assertEqual(self.api.dine_orders()[0]['payments'], [])
        order.add_payment({'pos_order_id': order.id, 'amount': 60,
                           'payment_method_id': method.id, 'card_brand': 'VISA',
                           'card_no': '4111 1111 1111 0083',
                           'cardholder_name': 'Private cardholder',
                           'payment_method_authcode': 'private-approval',
                           'ticket': 'private-terminal-receipt'})
        order._process_saved_order(False)
        models = ['pos.payment', 'payment.transaction', 'account.payment', 'account.move', 'loyalty.history']
        before = {model: self.env[model].search_count([]) for model in models}
        with self.as_customer():
            receipt = self.api.dine_orders()[0]
        payments = receipt['payments']
        self.assertEqual([p['amount'] for p in payments], [40, 60])
        self.assertEqual(payments[0]['method'], method.name)
        self.assertIsNone(payments[0]['card'])
        self.assertEqual(payments[1]['card'], {'brand': 'Visa', 'last4': '0083'})
        self.assertEqual(set(payments[1]), {'method', 'amount', 'currency', 'date', 'kind', 'card'})
        for secret in ['4111', 'Private cardholder', 'private-approval', 'private-terminal-receipt']:
            self.assertNotIn(secret, json.dumps(receipt))
        with self.as_customer(self.bob):
            self.assertEqual(self.api.dine_orders(), [])
        self.assertEqual(before, {model: self.env[model].search_count([]) for model in models})

    def test_card_details_allowlist_and_change_label(self):
        self.assertEqual(public_card_details('MASTERCARD', '**** **** **** 2745'),
                         {'brand': 'Mastercard', 'last4': '2745'})
        self.assertIsNone(public_card_details('4111111111111111', 'unknown'))
        self.assertIsNone(public_card_details(False, '123'))
        order = self._submitted_order()
        method = self.config.payment_method_ids[:1]
        order.add_payment({'pos_order_id': order.id, 'amount': 120,
                           'payment_method_id': method.id})
        order.add_payment({'pos_order_id': order.id, 'amount': -20,
                           'payment_method_id': method.id, 'is_change': True})
        order._process_saved_order(False)
        with self.as_customer():
            payments = self.api.dine_orders()[0]['payments']
        self.assertEqual([p['kind'] for p in payments], ['payment', 'change'])
        self.assertEqual(sum(p['amount'] for p in payments), order.amount_total)

    def test_price_edit_requires_new_review_and_unpublish_blocks_submission(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            self.product.list_price = 125
            changed = self.api.dine_submit(cart['basket_key'], cart['quote'])
            self.assertEqual(changed['status'], 'changed')
            self.assertEqual(changed['cart']['total'], 125)
            self.product.is_published = False
            latest = self.api.dine_submit(cart['basket_key'], changed['cart']['quote'])
            self.assertEqual(latest['status'], 'changed')
            self.assertFalse(latest['cart']['can_submit'])
        self.assertFalse(self.env['spx.mobile.submission'].sudo().search([('website_id', '=', self.website.id)]))

    def test_customer_cannot_mutate_another_basket_or_read_internal_models(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
        with self.as_customer(self.bob), self.assertRaises(UserError):
            self.api.dine_update(self.product.id, 0, cart['basket_key'])
        basket = self.env['spx.mobile.basket'].sudo().search([('partner_id', '=', self.alice.partner_id.id)])
        self.assertTrue(basket.items)
        with self.assertRaises(AccessError):
            basket.with_user(self.bob).read(['items'])

    def test_zero_total_stays_unpaid_for_staff(self):
        self.product.list_price = 0
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            received = self.api.dine_submit(cart['basket_key'], cart['quote'])
        order = self.env['pos.order'].search([('pos_reference', '=', received['order']['name'])])
        self.assertEqual(order.state, 'draft')
        self.assertFalse(order.payment_ids)

    def test_retry_after_source_order_removed_does_not_recreate_it(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            received = self.api.dine_submit(cart['basket_key'], cart['quote'])
        self.env['pos.order'].search([('pos_reference', '=', received['order']['name'])]).unlink()
        with self.as_customer():
            self.assertEqual(self.api.dine_submit(cart['basket_key'], cart['quote']), received)

    def test_closed_session_rejects_submission_without_creating_order(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
        self.config.current_session_id.state = 'closing_control'
        before = self.env['pos.order'].search_count([])
        with self.as_customer(), self.assertRaises(UserError):
            self.api.dine_submit(cart['basket_key'], cart['quote'])
        self.assertEqual(self.env['pos.order'].search_count([]), before)

    def test_order_history_excludes_other_customer(self):
        with self.as_customer():
            cart = self.api.dine_add(self.product.id, 1)
            received = self.api.dine_submit(cart['basket_key'], cart['quote'])
            self.assertIn(received['order']['name'], [o['name'] for o in self.api.dine_orders()])
        with self.as_customer(self.bob):
            self.assertEqual(self.api.dine_orders(), [])

    def test_guided_gift_and_birthday_templates_pass_native_pos_startup(self):
        action = self.website.action_mobile_setup_wizard()
        wizard = self.env['spx.mobile.setup.wizard'].browse(action['res_id'])
        wizard.write({'origin': 'https://dine-in.example.invalid',
                      'gift_mode': 'template', 'birthday_mode': 'template',
                      'birthday_enabled': True, 'signup_enabled': False})
        for unused in range(3):
            wizard.action_next()
        wizard.confirmed = True
        wizard.action_apply()
        self.config._check_before_creating_new_session()
        birthday = self.website.spx_birthday_program_id
        self.assertFalse(birthday.rule_ids.any_product)
        self.assertFalse(birthday.rule_ids.valid_product_ids)
        self.assertFalse(birthday._get_valid_products(self.product)[birthday.rule_ids])
        self.assertFalse(birthday.coupon_ids)
