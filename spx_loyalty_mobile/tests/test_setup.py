"""Setup safety and actionable validation on an isolated Odoo test database."""
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAppSetup(TransactionCase):
    def setUp(self):
        super().setUp()
        self.website = self.env['website'].create({
            'name': 'Setup test site', 'company_id': self.env.company.id,
            'domain': 'https://setup.example.invalid',
        })

    def program(self, name, **values):
        return self.env['loyalty.program'].create({
            'name': name, 'program_type': 'loyalty',
            'company_id': self.website.company_id.id,
            'currency_id': self.website.currency_id.id,
            'website_id': self.website.id, **values,
        })

    def test_detection_keeps_existing_choices_and_does_not_enable_features(self):
        selected = self.program('Selected')
        self.program('Another eligible program')
        self.website.write({
            'spx_mobile_account_origin': 'https://explicit.example.invalid',
            'spx_mobile_program_ids': [Command.set(selected.ids)],
        })
        before = self.env['loyalty.program'].search_count([])
        self.website.action_mobile_detect_settings()
        self.assertEqual(self.website.spx_mobile_account_origin, 'https://explicit.example.invalid')
        self.assertEqual(self.website.spx_mobile_program_ids, selected)
        self.assertEqual(self.website.spx_mobile_signup_program_id, selected)
        self.assertFalse(self.website.spx_mobile_enabled)
        self.assertFalse(self.website.spx_mobile_signup_enabled)
        self.assertEqual(self.env['loyalty.program'].search_count([]), before)

    def test_detection_does_not_guess_between_programs(self):
        self.program('Choice A')
        self.program('Choice B')
        self.website.action_mobile_detect_settings()
        self.assertFalse(self.website.spx_mobile_program_ids)
        self.assertFalse(self.website.spx_mobile_signup_program_id)
        self.assertEqual(self.website.spx_mobile_account_origin, self.website.domain)

    def test_multiwebsite_does_not_borrow_global_host(self):
        self.website.domain = False
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'https://other.example.invalid')
        self.assertGreater(self.env['website'].search_count([]), 1)
        self.assertFalse(self.website._mobile_origin_candidate())

    def test_program_domain_excludes_other_website_and_company(self):
        other_site = self.env['website'].search([('id', '!=', self.website.id)], limit=1)
        own = self.program('This site')
        other = self.program('Other site', website_id=other_site.id)
        shared = self.program('Shared', website_id=False, company_id=False)
        candidates = self.env['loyalty.program'].search(self.website._mobile_program_domain())
        self.assertIn(own, candidates)
        self.assertIn(shared, candidates)
        self.assertNotIn(other, candidates)
        with self.assertRaisesRegex(ValidationError, 'Other site.*another website'):
            with self.env.cr.savepoint():
                self.website.spx_mobile_program_ids = [Command.set(other.ids)]

    def test_signup_error_names_missing_fields_and_accepts_complete_setup(self):
        program = self.program('Signup')
        self.website.write({
            'spx_mobile_enabled': True,
            'spx_mobile_account_origin': self.website.domain,
            'spx_mobile_program_ids': [Command.set(program.ids)],
            'spx_mobile_signup_program_id': program.id,
            'spx_mobile_mail_from': 'accounts@example.invalid',
        })
        issues = self.website._mobile_signup_setup_issues()
        self.assertEqual(len(issues), 2)
        self.assertTrue(any('terms' in issue for issue in issues))
        self.assertTrue(any('privacy' in issue for issue in issues))
        with self.assertRaisesRegex(ValidationError, 'approved account and rewards terms'):
            with self.env.cr.savepoint():
                self.website.spx_mobile_signup_enabled = True
        self.website.write({
            'spx_mobile_terms': 'Test terms', 'spx_mobile_privacy': 'Test privacy',
            'spx_mobile_signup_enabled': True,
        })
        self.assertEqual(self.website._mobile_signup_config(), self.website.domain)

    def test_customer_cannot_use_setup_actions(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Setup portal test', 'login': 'setup-portal@example.invalid',
            'group_ids': [Command.set(self.env.ref('base.group_portal').ids)],
        })
        for method in ('action_mobile_detect_settings', 'action_mobile_programs',
                       'action_mobile_connection', 'action_mobile_optional_features',
                       'action_mobile_email_settings', 'action_mobile_setup'):
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(self.website.with_user(user), method)()

    def test_checklist_is_read_only_and_escapes_content(self):
        self.website.spx_mobile_brand = '<script>alert(1)</script>'
        before = (self.website.write_date, self.env['loyalty.program'].search_count([]),
                  self.env['mail.mail'].search_count([]), self.env['pos.order'].search_count([]))
        html = self.website.spx_mobile_setup_status
        self.assertIn('Needs setup', html)
        self.assertIn('Delivery test required', html)
        self.assertNotIn('<script>', html)
        self.assertEqual(before, (self.website.write_date, self.env['loyalty.program'].search_count([]),
                                 self.env['mail.mail'].search_count([]), self.env['pos.order'].search_count([])))
