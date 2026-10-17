"""Database-free tests of the actual setup validation and HTML renderer.

Import after odoo.init and addon-path configuration. Transactional install,
record rules and native views are covered separately by test_setup.py.
"""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from odoo.exceptions import AccessError, UserError
from odoo.addons.spx_loyalty_mobile.models import onboarding, setup


class TestSetupValidation(TestCase):
    def setUp(self):
        program = SimpleNamespace(active=True, program_type='loyalty', company_id=False, website_id=False)
        self.website = SimpleNamespace(
            env=SimpleNamespace(lang='en_US'),
            ensure_one=lambda: None, spx_mobile_enabled=True, spx_mobile_signup_enabled=True,
            spx_mobile_signup_program_id=program, spx_mobile_program_ids=[program],
            spx_mobile_terms='Approved test terms', spx_mobile_privacy='Approved test privacy',
            spx_mobile_policy_version='1', spx_mobile_mail_from='accounts@example.com',
            spx_mobile_account_origin='https://jennys.example/', company_id=1,
        )
        self.website._origin = self.website
        self.website._mobile_signup_setup_issues = lambda: onboarding.Website._mobile_signup_setup_issues(self.website)

    def test_complete_configuration_and_normalized_origin(self):
        self.assertEqual(self.website._mobile_signup_setup_issues(), [])
        self.assertEqual(onboarding.Website._mobile_signup_config(self.website), 'https://jennys.example')

    def test_only_missing_policy_fields_are_reported(self):
        self.website.spx_mobile_terms = '   '
        self.website.spx_mobile_privacy = False
        issues = self.website._mobile_signup_setup_issues()
        self.assertEqual(len(issues), 2)
        self.assertIn('terms', issues[0])
        self.assertIn('privacy', issues[1])

    def test_foreign_or_ineligible_signup_program_is_rejected(self):
        for field, value in [('active', False), ('program_type', 'promotion'),
                             ('company_id', 2), ('website_id', object())]:
            program = self.website.spx_mobile_signup_program_id
            previous = getattr(program, field)
            with self.subTest(field=field):
                setattr(program, field, value)
                self.assertEqual(len(self.website._mobile_signup_setup_issues()), 1)
                with self.assertRaises(UserError):
                    onboarding.Website._mobile_signup_config(self.website)
            setattr(program, field, previous)

    def test_bad_origin_and_sender_are_actionable_but_public_error_stays_generic(self):
        self.website.spx_mobile_account_origin = 'https://jennys.example/odoo'
        self.website.spx_mobile_mail_from = 'not-an-email'
        issues = self.website._mobile_signup_setup_issues()
        self.assertEqual(len(issues), 2)
        self.assertTrue(any('sender' in issue for issue in issues))
        self.assertTrue(any('HTTPS' in issue for issue in issues))
        with self.assertRaises(UserError) as error:
            onboarding.Website._mobile_signup_config(self.website)
        self.assertNotIn('sender', str(error.exception))
        self.assertNotIn('HTTPS', str(error.exception))

    def test_disabled_signup_remains_disabled_with_valid_fields(self):
        self.website.spx_mobile_signup_enabled = False
        self.assertFalse(self.website._mobile_signup_setup_issues())
        with self.assertRaises(UserError):
            onboarding.Website._mobile_signup_config(self.website)

    def test_checklist_escapes_all_three_columns(self):
        row = SimpleNamespace(_mobile_setup_rows=lambda: [
            ('<img src=x onerror=alert(1)>', '<script>bad</script>', '<a href=javascript:bad>bad</a>')])
        setup.Website._compute_mobile_setup_status([row])
        self.assertNotIn('<script>', row.spx_mobile_setup_status)
        self.assertNotIn('<img', row.spx_mobile_setup_status)
        self.assertNotIn('<a href', row.spx_mobile_setup_status)
        self.assertIn('&lt;script&gt;', row.spx_mobile_setup_status)

    def test_setup_admin_guard_precedes_record_access(self):
        row = SimpleNamespace(env=SimpleNamespace(is_system=lambda: False, lang='en_US'), check_access=Mock())
        with self.assertRaises(AccessError):
            setup.Website._mobile_setup_admin(row)
        row.check_access.assert_not_called()
