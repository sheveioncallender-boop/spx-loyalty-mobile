from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.addons.spx_loyalty_mobile.controllers.api import MobileAPI


@tagged('post_install', '-at_install')
class TestMobileScope(TransactionCase):
    """Run inside a real Odoo 19 database; these are not mocked ORM tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].search([], limit=1)
        cls.program = cls.env['loyalty.program'].create({
            'name': 'Mobile test loyalty', 'program_type': 'loyalty',
            'company_id': cls.website.company_id.id,
        })
        cls.website.write({'spx_mobile_enabled': True,
                           'spx_mobile_program_ids': [Command.set(cls.program.ids)]})
        cls.alice = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Mobile Alice', 'login': 'spx-mobile-alice',
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
        })
        cls.bob = cls.env['res.partner'].create({'name': 'Mobile Bob'})
        cls.own_card = cls.env['loyalty.card'].create({
            'program_id': cls.program.id, 'partner_id': cls.alice.partner_id.id, 'points': 321,
        })
        cls.other_card = cls.env['loyalty.card'].create({
            'program_id': cls.program.id, 'partner_id': cls.bob.id, 'points': 999,
        })
        cls.own_message = cls.env['spx.mobile.message'].create({
            'name': 'For Alice', 'body': 'Private customer message',
            'partner_id': cls.alice.partner_id.id, 'website_id': cls.website.id,
        })
        cls.other_message = cls.env['spx.mobile.message'].create({
            'name': 'For Bob', 'body': 'Private customer message',
            'partner_id': cls.bob.id, 'website_id': cls.website.id,
        })
        cls.controller = MobileAPI()

    def _request(self, user=None):
        return SimpleNamespace(env=self.env(user=(user or self.alice).id), website=self.website)

    def test_bootstrap_only_returns_own_cards_and_messages(self):
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', self._request()):
            data = self.controller.bootstrap()
        self.assertEqual([card['id'] for card in data['cards']], self.own_card.ids)
        self.assertEqual([m['id'] for m in data['messages']], self.own_message.ids)
        self.assertEqual(data['cards'][0]['points'], 321)
        self.assertFalse(data['capabilities']['push'])

    def test_other_customer_message_is_denied(self):
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', self._request()):
            with self.assertRaises(AccessError):
                self.controller.message_read(self.other_message.id)
        self.assertFalse(self.other_message.read_at)

    def test_portal_has_no_direct_model_access(self):
        with self.assertRaises(AccessError):
            self.other_message.with_user(self.alice).read(['body'])

    def test_disabled_website_is_denied(self):
        self.website.spx_mobile_enabled = False
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', self._request()):
            with self.assertRaises(AccessError):
                self.controller.bootstrap()

    def test_non_loyalty_program_rejected(self):
        other = self.env['loyalty.program'].create({'name': 'Not a loyalty program', 'program_type': 'gift_card'})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.website.spx_mobile_program_ids = other

    def test_preferences_cannot_change_other_customer(self):
        self.bob.spx_mobile_email = False
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', self._request()):
            self.controller.preferences(True)
        self.assertTrue(self.alice.partner_id.spx_mobile_email)
        self.assertFalse(self.bob.spx_mobile_email)

    def test_mobile_card_uses_native_pos_lookup_without_awarding_points(self):
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', self._request()):
            code = self.controller.bootstrap()['cards'][0]['number']
        self.assertEqual(code, self.own_card.code)
        # Native POS activateCode calls this lookup; order confirmation earns points.
        cards = self.env['loyalty.card']
        for _ in range(2):
            self.assertEqual(cards.get_loyalty_card_partner_by_code(code), self.alice.partner_id)
        self.assertEqual(self.own_card.points, 321)
        self.assertEqual(self.other_card.points, 999)
        self.assertFalse(cards.get_loyalty_card_partner_by_code('missing-mobile-test-code'))
