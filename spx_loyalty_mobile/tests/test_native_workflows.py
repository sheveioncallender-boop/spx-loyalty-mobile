"""Exercise setup templates through unmodified Odoo sale/loyalty workflows."""
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase, tagged

from ..controllers.api import MobileAPI
from ..controllers.engagement import EngagementAPI


@tagged('post_install', '-at_install')
class TestNativeWorkflows(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # All fixtures and orders live in the disposable test transaction.
        cls.env['loyalty.program'].search([]).active = False
        cls.website = cls.env['website'].create({
            'name': 'Native workflow checks', 'company_id': cls.env.company.id,
            'domain': 'https://native.example.invalid',
        })
        action = cls.website.action_mobile_setup_wizard()
        wizard = cls.env['spx.mobile.setup.wizard'].browse(action['res_id'])
        wizard.write({'gift_mode': 'template', 'gift_values': '50', 'signup_enabled': False})
        for unused in range(3):
            wizard.action_next()
        wizard.confirmed = True
        wizard.action_apply()
        cls.loyalty = cls.website.spx_mobile_program_ids
        cls.gift = cls.website.spx_gift_program_ids
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Native workflow member', 'login': 'native-workflow@example.invalid',
            'group_ids': [Command.set(cls.env.ref('base.group_portal').ids)],
            'spx_mobile_legacy_access': True,
        })
        cls.partner = cls.user.partner_id
        cls.product = cls.env['product.product'].create({
            'name': 'Native workflow service', 'type': 'service', 'list_price': 100,
            'taxes_id': [Command.clear()],
        })

    def order(self, amount=100, product=None, quantity=1):
        return self.env['sale.order'].with_context(loyalty_no_mail=True).create({
            'partner_id': self.partner.id, 'website_id': self.website.id,
            'company_id': self.website.company_id.id,
            'order_line': [Command.create({
                'product_id': (product or self.product).id,
                'product_uom_qty': quantity, 'price_unit': amount,
                'tax_ids': [Command.clear()],
            })],
        })

    def bootstrap(self):
        req = SimpleNamespace(env=self.env(user=self.user.id), website=self.website)
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', req):
            return MobileAPI().bootstrap()

    def wallet(self):
        req = SimpleNamespace(env=self.env(user=self.user.id), website=self.website)
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', req), \
                patch('odoo.addons.spx_loyalty_mobile.controllers.engagement.request', req):
            return EngagementAPI().wallet()

    def test_existing_loyalty_card_earns_redeems_and_restores_on_cancel(self):
        card = self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'program_id': self.loyalty.id, 'partner_id': self.partner.id, 'points': 0,
        })
        # This is the same lookup native POS uses when scanning the app barcode.
        code = self.bootstrap()['cards'][0]['number']
        self.assertEqual(code, card.code)
        self.assertEqual(self.env['loyalty.card'].get_loyalty_card_partner_by_code(code), self.partner)
        purchase = self.order()
        purchase._update_programs_and_rewards()
        self.assertEqual(card.points, 0, 'A draft order must not award points')
        purchase.action_confirm()
        self.assertEqual(card.points, 100)
        self.assertEqual(self.bootstrap()['cards'][0]['points'], 100)
        self.assertEqual(self.loyalty.coupon_ids, card, 'Reuse the existing native card')

        redemption = self.order(amount=40)
        redemption._update_programs_and_rewards()
        self.assertIn(self.loyalty.reward_ids, redemption._get_claimable_rewards()[card])
        result = redemption._apply_program_reward(self.loyalty.reward_ids, card)
        self.assertNotIn('error', result)
        self.assertEqual(redemption.amount_total, 36)
        self.assertEqual(card.points, 100, 'Draft redemption must not spend the balance')
        redemption.action_confirm()
        # Odoo awards 40 points and spends 100; its own loyalty discount is excluded
        # from earning calculations. The connector must reflect that native rule.
        self.assertEqual(card.points, 40)
        self.assertEqual(self.bootstrap()['cards'][0]['points'], 40)
        redemption._action_cancel()
        self.assertEqual(card.points, 100)
        purchase._action_cancel()
        self.assertEqual(card.points, 0)
        self.assertEqual(self.loyalty.coupon_ids, card)

    def test_native_gift_purchase_splits_cards_and_hides_unpaid_codes(self):
        product = self.website.spx_gift_product_ids.product_variant_id
        purchase = self.order(amount=50, product=product, quantity=2)
        purchase._update_programs_and_rewards()
        cards = purchase._get_reward_coupons().filtered(lambda c: c.program_id == self.gift)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards.mapped('points'), [0, 0])
        self.assertFalse(self.wallet()['gift_cards'])
        purchase.action_confirm()
        self.assertEqual(cards.mapped('points'), [50, 50])
        self.assertTrue(all(c.order_id == purchase for c in cards))
        self.assertFalse(purchase._is_paid())
        self.assertFalse(self.wallet()['gift_cards'], 'Confirmation alone is not captured payment')
        purchase._action_cancel()
        self.assertFalse(cards.exists())
        self.assertFalse(self.wallet()['gift_cards'])

    def test_native_gift_redemption_and_cancellation_update_same_wallet_card(self):
        card = self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'program_id': self.gift.id, 'partner_id': self.partner.id, 'points': 100,
        })
        before = self.wallet()['gift_cards'][0]
        self.assertEqual((before['id'], before['number'], before['balance']), (card.id, card.code, 100))
        redemption = self.order(amount=40)
        status = redemption._try_apply_code(card.code)
        self.assertNotIn('error', status)
        self.assertEqual(status[card], self.gift.reward_ids)
        self.assertNotIn('error', redemption._apply_program_reward(status[card], card))
        self.assertEqual(redemption.amount_total, 0)
        self.assertEqual(card.points, 100)
        redemption.action_confirm()
        self.assertEqual(card.points, 60)
        self.assertEqual(self.wallet()['gift_cards'][0]['balance'], 60)
        redemption._action_cancel()
        self.assertEqual(card.points, 100)
        after = self.wallet()['gift_cards'][0]
        self.assertEqual((after['id'], after['number'], after['balance']), (card.id, card.code, 100))
