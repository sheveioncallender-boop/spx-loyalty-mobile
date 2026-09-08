"""Native HTTP/ORM checks; run only in a disposable Odoo test database.

These exercise real request website/pricelist/cart initialization and native
cart models. HttpCase.authenticate establishes a test session; it does not
validate a production password, MFA, reverse proxy or Android cookie bridge.
"""
from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestMobileCartHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.website.write({'spx_mobile_enabled': True, 'prevent_zero_price_sale': True})
        cls.alice, cls.bob = cls.env['res.users'].with_context(no_reset_password=True).create([
            {
                'name': name, 'login': login,
                'company_id': cls.website.company_id.id,
                'company_ids': [Command.set(cls.website.company_id.ids)],
                'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
            }
            for name, login in [('Mobile HTTP Alice', 'spx-mobile-http-alice'),
                                ('Mobile HTTP Bob', 'spx-mobile-http-bob')]
        ])
        cls.product, cls.free_product, cls.hidden_product = cls.env['product.product'].create([
            {
                'name': name, 'list_price': price, 'type': 'service', 'sale_ok': True,
                'website_id': cls.website.id, 'is_published': published,
                'website_sequence': -10000, 'taxes_id': [Command.clear()],
            }
            for name, price, published in [('Mobile HTTP item', 125, True),
                                           ('Mobile HTTP zero item', 0, True),
                                           ('Mobile HTTP private item', 50, False)]
        ])

    def _rpc(self, path, params=None, error=False):
        response = self.url_open(path, json={
            'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': params or {},
        })
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        if error:
            self.assertIn('error', data, data)
            return data['error']
        self.assertNotIn('error', data, data)
        return data['result']

    def _native_price(self, product, qty):
        return self._rpc('/website_sale/get_combination_info', {
            'product_template_id': product.product_tmpl_id.id,
            'product_id': product.id, 'combination': [], 'add_qty': qty,
        })

    def test_native_pricing_cart_session_and_duplicate_add(self):
        self.authenticate(self.alice.login, 'test-session')
        catalog = self._rpc('/spx/mobile/v1/catalog')
        item = next(item for item in catalog['items'] if item['product_id'] == self.product.id)
        self.assertAlmostEqual(item['price'], self._native_price(self.product, 1)['price'])
        self.assertTrue(item['direct_add'])
        native_price = self._native_price(self.product, 2)['price']
        params = {'product_id': self.product.id, 'qty': 2, 'request_id': 'http-native-price-001'}
        added = self._rpc('/spx/mobile/v1/cart/add', params)
        repeated = self._rpc('/spx/mobile/v1/cart/add', params)
        restored = self._rpc('/spx/mobile/v1/cart')
        self.assertEqual(added['id'], restored['id'])
        self.assertEqual(added['lines'], repeated['lines'])
        line = next(line for line in restored['lines'] if line['editable'])
        self.assertEqual(line['qty'], 2)
        self.assertAlmostEqual(line['total'], native_price * 2, places=2)
        self.env.invalidate_all()
        order = self.env['sale.order'].browse(added['id'])
        self.assertEqual(order.partner_id, self.alice.partner_id)
        self.assertEqual(order.website_id, self.website)
        self.assertEqual(order.company_id, self.website.company_id)
        self.assertEqual(order.state, 'draft')
        self.assertAlmostEqual(restored['total'], order.amount_total, places=2)
        self.assertEqual(restored['currency'], order.currency_id.name)
        removed = self._rpc('/spx/mobile/v1/cart/update', {'line_id': line['id'], 'qty': 0})
        self.assertNotIn(line['id'], [item['id'] for item in removed['lines']])

    def test_zero_price_and_unpublished_products_are_blocked(self):
        self.authenticate(self.alice.login, 'test-session')
        self.assertTrue(self._native_price(self.free_product, 1)['prevent_zero_price_sale'])
        for product in (self.free_product, self.hidden_product):
            error = self._rpc('/spx/mobile/v1/cart/add', {
                'product_id': product.id, 'qty': 1,
                'request_id': 'http-unavailable-%s' % product.id,
            }, error=True)
            self.assertEqual(error['data']['name'], 'odoo.exceptions.UserError')

    def test_other_customer_cannot_change_existing_cart(self):
        self.authenticate(self.alice.login, 'test-session')
        added = self._rpc('/spx/mobile/v1/cart/add', {
            'product_id': self.product.id, 'qty': 1, 'request_id': 'http-own-customer-001',
        })
        line = next(line for line in added['lines'] if line['editable'])
        self.authenticate(self.bob.login, 'test-session')
        error = self._rpc('/spx/mobile/v1/cart/update', {
            'line_id': line['id'], 'qty': 0,
        }, error=True)
        self.assertEqual(error['data']['name'], 'odoo.exceptions.AccessError')
        self.env.invalidate_all()
        self.assertEqual(self.env['sale.order.line'].browse(line['id']).product_uom_qty, 1)
