"""Legacy APK ordering endpoints must fail closed after the dine-in upgrade."""
from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestLegacyCartHttp(HttpCase):
    def test_retired_routes_create_no_sale_or_pos_order(self):
        website = self.env['website'].get_current_website()
        website.spx_mobile_enabled = True
        guest = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Legacy app guest', 'login': 'spx-legacy-app-guest',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
            'spx_mobile_legacy_access': True,
        })
        self.authenticate(guest.login, 'test-session')
        sales_before = self.env['sale.order'].search_count([])
        pos_before = self.env['pos.order'].search_count([])
        for suffix in ['catalog', 'cart', 'cart/add', 'cart/update', 'cart/reward']:
            response = self.url_open('/spx/mobile/v1/' + suffix, json={
                'jsonrpc': '2.0', 'id': 1, 'method': 'call', 'params': {},
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['error']['data']['name'], 'odoo.exceptions.UserError')
        self.env.invalidate_all()
        self.assertEqual(self.env['sale.order'].search_count([]), sales_before)
        self.assertEqual(self.env['pos.order'].search_count([]), pos_before)
