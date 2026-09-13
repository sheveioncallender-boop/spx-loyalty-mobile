from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from odoo.addons.spx_loyalty_mobile.controllers.api import MobileAPI
from urllib.parse import urlparse, parse_qs
from lxml import html

from odoo import Command, fields
from odoo.exceptions import UserError, AccessError, AccessDenied
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMobileOnboarding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Account mails use native post-commit delivery. Database tests inspect
        # their records and must never send real email (Odoo sends synchronously
        # from send_after_commit when current_test is set).
        cls.delivery_patch = patch.object(type(cls.env['mail.mail']), 'send_after_commit', autospec=True)
        cls.delivery_mock = cls.delivery_patch.start()
        cls.addClassCleanup(cls.delivery_patch.stop)
        cls.website = cls.env['website'].search([], limit=1)
        cls.program = cls.env['loyalty.program'].create({'name': 'Signup test program', 'program_type': 'loyalty',
            'company_id': cls.website.company_id.id})
        cls.website.write({'spx_mobile_enabled': True, 'spx_mobile_program_ids': [Command.set(cls.program.ids)],
            'spx_mobile_signup_program_id': cls.program.id, 'spx_mobile_account_origin': 'https://jennys.example',
            'spx_mobile_mail_from': 'no-reply@example.com', 'spx_mobile_terms': 'Test terms.',
            'spx_mobile_privacy': 'Test privacy.', 'spx_mobile_policy_version': 'test-1', 'spx_mobile_signup_enabled': True})
        cls.service = cls.env['spx.mobile.registration']
        cls.values = {'first_name': 'Alex', 'last_name': 'Joseph', 'phone': '555 0123',
            'email': 'new.member@example.com', 'password': 'Sample-password-928!', 'birthday': '1990-01-12',
            'city': 'Port of Spain', 'marketing_email': False, 'marketing_sms': False, 'terms': True, 'policy_version': 'test-1'}

    def signup(self, **overrides):
        values = dict(self.values, **overrides)
        receipt = self.service._signup(self.website, values)
        return self.service.search([('email', '=', values['email'])], order='id desc', limit=1), receipt

    def token(self, record):
        link = html.fromstring(record.mail_id.body_html).xpath('//a/@href')[0]
        return parse_qs(urlparse(link).query)['token'][0]

    def test_account_mail_link_and_admin_send_result_write(self):
        public = self.env.ref('base.public_user')
        self.service.with_user(public)._signup(self.website.sudo(), self.values)
        record = self.service.search([('email', '=', self.values['email'])], limit=1)
        mail = record.mail_id
        self.assertEqual(mail.model, record._name)
        self.assertEqual(mail.res_id, record.id)
        self.assertEqual(mail.create_uid, self.env.ref('base.user_root'))
        self.delivery_mock.assert_called()
        admin = self.env.ref('base.user_admin')
        # Reproduce the delegated Message-Id write in native mail.mail._send.
        mail.with_user(admin).write({'message_id': '<signup-test@example.invalid>'})
        with self.assertRaises(AccessError):
            record.with_user(admin).write({'state': 'done'})
        for user in (self.env.ref('base.public_user'), self.env.ref('base.default_user')):
            with self.assertRaises(AccessError):
                mail.mail_message_id.with_user(user).read(['body'])
            with self.assertRaises(AccessError):
                mail.mail_message_id.with_user(user).write({'message_id': '<forbidden@example.invalid>'})

    def test_repair_links_existing_registration_mail_without_sending(self):
        record, _ = self.signup()
        mail = record.mail_id
        mail.sudo().write({'model': False, 'res_id': False})
        admin = self.env.ref('base.user_admin')
        with self.assertRaises(AccessError):
            mail.with_user(admin).write({'message_id': '<before-repair@example.invalid>'})
        self.delivery_mock.reset_mock()
        self.service._repair_account_mail_links()
        self.assertEqual((mail.model, mail.res_id), (record._name, record.id))
        mail.with_user(admin).write({'message_id': '<after-repair@example.invalid>'})
        self.service._repair_account_mail_links()
        self.delivery_mock.assert_not_called()

    def test_pending_has_no_user_and_hash_is_not_plaintext(self):
        record, _ = self.signup()
        self.assertFalse(self.service._users(record.email))
        self.assertNotEqual(record.password_hash, self.values['password'])
        self.assertTrue(self.env['res.users']._crypt_context().verify(self.values['password'], record.password_hash))
        with self.assertRaises(AccessDenied):
            self.env['res.users']._login({'type': 'password', 'login': record.email, 'password': self.values['password']}, {})

    def test_verify_creates_portal_and_card_once(self):
        record, _ = self.signup()
        token = self.token(record)
        self.assertEqual(self.service._token(self.website, token, 'signup'), record)
        user = record._complete(password=self.values['password'])
        self.assertTrue(user.has_group('base.group_portal'))
        self.assertFalse(user.has_group('base.group_user'))
        self.assertTrue(user.share)
        self.assertEqual(record.card_id.partner_id, user.partner_id)
        self.assertEqual(record.card_id.points, 0)
        self.assertEqual(record.card_id.program_id, self.program)
        self.assertFalse(record.password_hash)
        with self.assertRaises(UserError):
            self.service._token(self.website, token, 'signup')
        with self.assertRaises(UserError):
            record._complete(password=self.values['password'])
        self.assertEqual(self.env['loyalty.card'].search_count([('partner_id', '=', user.partner_id.id), ('program_id', '=', self.program.id)]), 1)

    def test_existing_contact_card_and_points_preserved(self):
        partner = self.env['res.partner'].create({'name': 'Existing member', 'email': self.values['email']})
        card = self.env['loyalty.card'].create({'partner_id': partner.id, 'program_id': self.program.id, 'points': 87})
        record, _ = self.signup()
        record._complete(password=self.values['password'])
        self.assertEqual(record.partner_id, partner)
        self.assertEqual(record.card_id, card)
        self.assertEqual(card.points, 87)
        self.assertEqual(partner.name, 'Existing member')

    def test_second_signup_cannot_overwrite_existing_user_password(self):
        record, _ = self.signup()
        record._complete(password=self.values['password'])
        count = self.service.search_count([('email', '=', record.email)])
        self.service._signup(self.website, dict(self.values, password='Attacker-password-123!'))
        self.assertEqual(self.service.search_count([('email', '=', record.email)]), count)
        self.env.cr.execute('SELECT password FROM res_users WHERE id=%s', (record.user_id.id,))
        stored = self.env.cr.fetchone()[0]
        self.assertTrue(self.env['res.users']._crypt_context().verify(self.values['password'], stored))

    def test_new_verification_invalidates_other_pending_signups(self):
        older, _ = self.signup(password='Older-password-123!')
        newer, _ = self.signup()
        newer._complete(password=self.values['password'])
        self.assertEqual(older.state, 'expired')
        self.assertFalse(older.password_hash)
        with self.assertRaises(UserError):
            older._complete(password=self.values['password'])

    def test_expired_or_cross_website_token_rejected(self):
        record, _ = self.signup()
        token = self.token(record)
        other = self.env['website'].create({'name': 'Another site'})
        with self.assertRaises(UserError):
            self.service._token(other, token, 'signup')
        record.expires_at = fields.Datetime.now()-timedelta(seconds=1)
        with self.assertRaises(UserError):
            self.service._token(self.website, token, 'signup')

    def test_resend_rotates_token_only_for_matching_receipt(self):
        record, receipt = self.signup()
        original = record.token_hash
        self.service._resend(self.website, 'wrong-receipt-'+'x'*32)
        self.assertEqual(record.token_hash, original)
        record.sent_at = fields.Datetime.now()-timedelta(minutes=2)
        self.service._resend(self.website, receipt)
        self.assertNotEqual(record.token_hash, original)

    def test_reset_changes_native_password_and_is_single_use(self):
        record, _ = self.signup()
        record._complete(password=self.values['password'])
        self.service._forgot(self.website, record.email)
        reset = self.service.search([('kind', '=', 'reset'), ('email', '=', record.email)], limit=1)
        reset._complete(password='Fresh-password-234!')
        self.env.cr.execute('SELECT password FROM res_users WHERE id=%s', (record.user_id.id,))
        stored = self.env.cr.fetchone()[0]
        self.assertTrue(self.env['res.users']._crypt_context().verify('Fresh-password-234!', stored))
        self.assertFalse(self.env['res.users']._crypt_context().verify(self.values['password'], stored))
        with self.assertRaises(UserError):
            reset._complete(password='Another-password-234!')

    def test_reset_never_targets_internal_user(self):
        self.service._forgot(self.website, self.env.user.email or 'admin@example.com')
        self.assertFalse(self.service.search([('kind', '=', 'reset')]))

    def test_ambiguous_partner_match_does_not_merge(self):
        for name in ['First contact', 'Second contact']:
            self.env['res.partner'].create({'name': name, 'email': self.values['email']})
        record, _ = self.signup()
        with self.assertRaises(UserError):
            record._complete(password=self.values['password'])
        self.assertFalse(self.service._users(record.email))

    def test_validation_and_policy_version_enforced(self):
        for change in [{'terms': False}, {'policy_version': 'stale'}, {'birthday': '2099-01-01'},
                       {'birthday': '2001-02-30'}, {'password': 'short'}, {'phone': '123'}, {'marketing_sms': 'true'}]:
            with self.assertRaises(UserError):
                self.service._signup(self.website, dict(self.values, **change))

    def test_portal_cannot_read_registration_or_call_service(self):
        record, _ = self.signup()
        user = record._complete(password=self.values['password'])
        with self.assertRaises(AccessError):
            record.with_user(user).read(['email'])

    def test_native_unverified_account_cannot_bypass_app_verification(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Unverified', 'login': 'unverified@example.com', 'email': 'unverified@example.com',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })
        with patch('odoo.addons.spx_loyalty_mobile.controllers.api.request',
                   SimpleNamespace(env=self.env(user=user.id), website=self.website)):
            with self.assertRaises(AccessError):
                MobileAPI()._scope()

    def test_verification_requires_password_from_same_signup(self):
        record, _ = self.signup()
        with self.assertRaises(UserError):
            record._complete(password='Different-password-123!')
        self.assertFalse(self.service._users(record.email))
        self.assertEqual(record.state, 'pending')
