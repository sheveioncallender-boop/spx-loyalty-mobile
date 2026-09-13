"""Native ORM integration checks. Run on a disposable Odoo 19 database."""
from contextlib import contextmanager
import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.spx_loyalty_mobile.controllers.dine_in import DineInAPI


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
            cls.config.current_session_id.action_pos_session_open()
        cls.website = cls.env['website'].create({'name': 'Dine-in tests', 'company_id': cls.config.company_id.id,
                                                'spx_mobile_enabled': True, 'spx_mobile_pos_config_id': cls.config.id})
        cls.alice, cls.bob = cls.env['res.users'].with_context(no_reset_password=True).create([
            {'name': name, 'login': login, 'company_id': cls.config.company_id.id,
             'company_ids': [Command.set(cls.config.company_id.ids)],
             'group_ids': [Command.set([cls.env.ref('base.group_portal').id])]}
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
    def customer(self, user=None):
        req = SimpleNamespace(env=self.env(user=(user or self.alice).id), website=self.website)
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', req), \
             patch('odoo.addons.spx_loyalty_mobile.controllers.dine_in.request', req):
            yield

    def test_quote_and_submit_native_unpaid_order_and_replay(self):
        before = self.env['pos.order'].search_count([])
        with self.customer():
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
        self.assertEqual(order.lines.product_id, self.product)
        self.assertEqual(order.amount_total, cart['total'])
        tags = json.loads(order.internal_note)
        self.assertIsInstance(tags, list)
        self.assertTrue(all(isinstance(tag.get('text'), str) for tag in tags))
        self.assertTrue(all(isinstance(tag.get('colorIndex'), int) for tag in tags))

    def test_price_edit_requires_new_review_and_unpublish_blocks_submission(self):
        with self.customer():
            cart = self.api.dine_add(self.product.id, 1)
            self.product.list_price = 125
            changed = self.api.dine_submit(cart['basket_key'], cart['quote'])
            self.assertEqual(changed['status'], 'changed')
            self.assertEqual(changed['cart']['total'], 125)
            self.product.is_published = False
            latest = self.api.dine_submit(cart['basket_key'], changed['cart']['quote'])
            self.assertEqual(latest['status'], 'changed')
            self.assertFalse(latest['cart']['can_submit'])
        self.assertFalse(self.env['spx.mobile.submission'].search([('website_id', '=', self.website.id)]))

    def test_customer_cannot_mutate_another_basket_or_read_internal_models(self):
        with self.customer():
            cart = self.api.dine_add(self.product.id, 1)
        with self.customer(self.bob), self.assertRaises(UserError):
            self.api.dine_update(self.product.id, 0, cart['basket_key'])
        basket = self.env['spx.mobile.basket'].search([('partner_id', '=', self.alice.partner_id.id)])
        self.assertTrue(basket.items)
        with self.assertRaises(AccessError):
            basket.with_user(self.bob).read(['items'])

    def test_zero_total_stays_unpaid_for_staff(self):
        self.product.list_price = 0
        with self.customer():
            cart = self.api.dine_add(self.product.id, 1)
            received = self.api.dine_submit(cart['basket_key'], cart['quote'])
        order = self.env['pos.order'].search([('pos_reference', '=', received['order']['name'])])
        self.assertEqual(order.state, 'draft')
        self.assertFalse(order.payment_ids)

    def test_retry_after_source_order_removed_does_not_recreate_it(self):
        with self.customer():
            cart = self.api.dine_add(self.product.id, 1)
            received = self.api.dine_submit(cart['basket_key'], cart['quote'])
        self.env['pos.order'].search([('pos_reference', '=', received['order']['name'])]).unlink()
        with self.customer():
            self.assertEqual(self.api.dine_submit(cart['basket_key'], cart['quote']), received)
