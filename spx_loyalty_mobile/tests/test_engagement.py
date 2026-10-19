from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.addons.spx_loyalty_mobile.controllers.engagement import EngagementAPI
from odoo.addons.spx_loyalty_mobile.models.engagement import birthday_in_year


@tagged('post_install', '-at_install')
class TestMemberExtras(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].search([], limit=1)
        cls.loyalty = cls.env['loyalty.program'].create({'name': 'Member extras test', 'program_type': 'loyalty', 'company_id': cls.website.company_id.id})
        cls.gift = cls.env['loyalty.program'].create({'name': 'Purchased gift test', 'program_type': 'gift_card', 'company_id': cls.website.company_id.id})
        cls.birthday = cls.env['loyalty.program'].create({'name': 'Birthday credit test', 'program_type': 'gift_card', 'company_id': cls.website.company_id.id})
        cls.birthday.trigger_product_ids = False
        cls.website.write({'spx_mobile_enabled': True, 'spx_mobile_program_ids': [Command.set(cls.loyalty.ids)],
            'spx_birthday_program_id': cls.birthday.id, 'spx_birthday_amount': 100, 'spx_birthday_enabled': True,
            'spx_gift_program_ids': [Command.set(cls.gift.ids)], 'spx_mobile_mail_from': 'no-reply@example.invalid'})
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Extras Alice', 'email': 'extras-alice@example.invalid', 'login': 'extras-alice@example.invalid',
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])], 'spx_mobile_legacy_access': True})
        cls.partner = cls.user.partner_id
        cls.partner.spx_mobile_birthday = date(1990, 9, 23)
        cls.env['loyalty.card'].with_context(loyalty_no_mail=True).create({'program_id': cls.loyalty.id, 'partner_id': cls.partner.id})
        cls.controller = EngagementAPI()

    def request_patches(self):
        req = SimpleNamespace(env=self.env(user=self.user.id), website=self.website)
        return (patch('odoo.addons.spx_loyalty_mobile.controllers.api.request', req),
                patch('odoo.addons.spx_loyalty_mobile.controllers.engagement.request', req))

    def card(self, **vals):
        return self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'program_id': self.gift.id, 'points': 250, **vals})

    def test_birthday_only_once_and_inclusive_21_days(self):
        today = date(2026, 9, 23)
        with patch.object(type(self.website), '_spx_today', return_value=today):
            self.env['spx.mobile.birthday.award']._cron_birthdays()
            self.env['spx.mobile.birthday.award']._cron_birthdays()
        awards = self.env['spx.mobile.birthday.award'].search([('partner_id', '=', self.partner.id)])
        self.assertEqual(len(awards), 1)
        self.assertEqual(awards.card_id.points, 100)
        self.assertEqual(awards.card_id.expiration_date, today + timedelta(days=20))
        self.assertEqual(sum(awards.card_id.history_ids.mapped('issued')), 100)
        self.website.spx_birthday_amount = 175
        self.assertEqual(awards.card_id.points, 100)
        self.assertEqual(birthday_in_year(date(2000, 2, 29), 2027), date(2027, 2, 28))
        self.assertEqual(birthday_in_year(date(2000, 2, 29), 2028), date(2028, 2, 29))

    def test_credit_and_purchased_programs_cannot_mix(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.website.spx_gift_program_ids = self.birthday

    def test_announcements_are_idempotent_and_respect_opt_out(self):
        a = self.env['spx.mobile.announcement'].create({'name': 'Karaoke', 'body': 'Friday night', 'website_id': self.website.id})
        a.action_publish()
        a.action_publish()
        self.assertEqual(len(a.message_ids.filtered(lambda m: m.partner_id == self.partner)), 1)
        self.partner.spx_member_announcements = False
        b = a.copy({'name': 'Latin night'})
        b.action_publish()
        self.assertFalse(b.message_ids.filtered(lambda m: m.partner_id == self.partner))

    def test_wallet_never_exposes_another_member_or_unpaid_purchase(self):
        own = self.card(partner_id=self.partner.id)
        other = self.card(partner_id=self.env.ref('base.partner_root').id)
        order = self.env['sale.order'].create({'partner_id': self.partner.id, 'company_id': self.website.company_id.id})
        draft = self.card(order_id=order.id)
        p1, p2 = self.request_patches()
        with p1, p2:
            ids = [c['id'] for c in self.controller.wallet()['gift_cards']]
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)
        self.assertNotIn(draft.id, ids)

    def test_old_app_cannot_claim_an_unassigned_card(self):
        card = self.card()
        p1, p2 = self.request_patches()
        with p1, p2:
            with self.assertRaises(UserError):
                self.controller.add_gift(card.code)
        self.assertFalse(card.partner_id)

    def test_native_birthday_assignment_appears_without_award_or_claim(self):
        card = self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'program_id': self.birthday.id, 'partner_id': self.partner.id, 'points': 80})
        p1, p2 = self.request_patches()
        with p1, p2:
            cards = self.controller.wallet()['birthday_credits']
        self.assertEqual([c['id'] for c in cards], [card.id])
        self.assertEqual(cards[0]['number'], card.code)
        card.points = 35
        with p1, p2:
            self.assertEqual(self.controller.wallet()['birthday_credits'][0]['balance'], 35)

    def test_staff_issue_is_once_and_adjustment_is_native(self):
        wizard = self.env['spx.mobile.birthday.issue'].create({
            'website_id': self.website.id, 'partner_id': self.partner.id,
            'amount': 75, 'days': 21, 'reason': 'Approved birthday test'})
        action = wizard.action_issue()
        wizard.action_issue()
        award = self.env['spx.mobile.birthday.award'].search([('partner_id', '=', self.partner.id)])
        self.assertEqual(len(award), 1)
        self.assertEqual(action['res_model'], 'loyalty.card')
        self.assertEqual(action['res_id'], award.card_id.id)
        self.assertEqual(award.card_id.points, 75)
        self.assertEqual(award.action_adjust_native_balance()['res_model'], 'loyalty.card.update.balance')
        self.assertEqual(award.card_id.expiration_date, self.website._spx_today() + timedelta(days=20))
        self.assertEqual(sum(award.card_id.history_ids.mapped('issued')), 75)

    def test_customer_birthdays_include_nonmembers_and_respect_audience(self):
        customer = self.env['res.partner'].create({'name': 'Walk-in customer', 'spx_mobile_birthday': date(1990, 9, 23)})
        self.assertIn(customer, self.website._spx_birthday_customers())
        with patch.object(type(self.website), '_spx_today', return_value=date(2026, 9, 23)):
            self.env['spx.mobile.birthday.award']._cron_birthdays()
            self.assertFalse(self.env['spx.mobile.birthday.award'].search([('partner_id', '=', customer.id)]))
            self.website.spx_birthday_audience = 'customers'
            self.env['spx.mobile.birthday.award']._cron_birthdays()
            self.assertEqual(len(self.env['spx.mobile.birthday.award'].search([('partner_id', '=', customer.id)])), 1)
            view = customer.with_context(spx_birthday_website_id=self.website.id)
            self.assertEqual(view.spx_birthday_countdown, 0)
            self.assertEqual(view.spx_birthday_balance, 100)
            self.assertEqual(view.spx_birthday_remaining, 21)
            # Odoo 19 normalizes '=' to 'in' before calling custom search methods.
            self.assertIn(customer, self.env['res.partner'].with_context(
                spx_birthday_website_id=self.website.id).search([('spx_birthday_countdown', '=', 0)]))

    def test_portal_user_cannot_issue_or_inspect_birthdays(self):
        with self.assertRaises(AccessError):
            self.website.with_user(self.user).action_spx_birthday_customers()
        with self.assertRaises(AccessError):
            self.env['spx.mobile.birthday.issue'].with_user(self.user).create({
                'website_id': self.website.id, 'partner_id': self.partner.id, 'amount': 1, 'days': 21})

    def test_configured_existing_birthday_field_is_read_without_copying(self):
        field = self.env['ir.model.fields'].create({'name': 'x_existing_birthday', 'field_description': 'Existing birthday',
            'model_id': self.env.ref('base.model_res_partner').id, 'ttype': 'date', 'state': 'manual'})
        self.website.spx_birthday_field_id = field
        self.partner.write({'x_existing_birthday': date(1985, 12, 31)})
        self.assertEqual(self.website._spx_birth_date(self.partner), date(1985, 12, 31))
        self.assertEqual(self.partner.spx_mobile_birthday, date(1990, 9, 23))
        self.partner.x_existing_birthday = False
        self.assertEqual(self.website._spx_birth_date(self.partner), self.partner.spx_mobile_birthday)

    def test_send_is_idempotent_reuses_contact_and_creates_no_user(self):
        c = self.card(partner_id=self.partner.id)
        recipient = self.env['res.partner'].create({'name': 'Gift recipient', 'email': 'gift-recipient@example.invalid'})
        user_count = self.env['res.users'].search_count([])
        p1, p2 = self.request_patches()
        with p1, p2, patch.object(self.controller, '_gift_rate'):
            values = dict(card_id=c.id, recipient_email=recipient.email, recipient_name='Recipient', message='Enjoy!', key='gift-request-123456789')
            self.controller.send_gift(**values)
            self.controller.send_gift(**values)
        delivery = self.env['spx.mobile.gift.delivery'].search([('card_id', '=', c.id)])
        self.assertEqual(len(delivery), 1)
        self.assertEqual(c.partner_id, recipient)
        self.assertEqual(self.env['res.users'].search_count([]), user_count)
        self.assertEqual(delivery.mail_id.state, 'outgoing')
        self.assertEqual(delivery.mail_id.model, 'spx.mobile.gift.delivery')
        # Match the native retry path without making an SMTP connection.
        delivery.mail_id.with_user(self.env.ref('base.user_admin')).write({'message_id': '<gift-retry@example.invalid>'})
        self.assertEqual(delivery.mail_id.message_id, '<gift-retry@example.invalid>')
        with self.assertRaises(AccessError):
            delivery.with_user(self.user).read(['recipient_email'])
