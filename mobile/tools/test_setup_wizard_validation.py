"""Run without a database after configuring Odoo's addon path."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from odoo.exceptions import AccessError, UserError
from odoo.addons.spx_loyalty_mobile.models.setup_wizard import AppSetupWizard, gift_amounts


class TestWizardValidation(TestCase):
    def test_amounts_accept_positive_unique_values_and_keep_order(self):
        self.assertEqual(gift_amounts(' 100, 50.50, 200 '), [100, 50.5, 200])

    def test_amounts_reject_nonfinite_duplicates_and_unbounded_inputs(self):
        for value in ('', '0', '-1', 'NaN', 'Infinity', '1e999999', '50,50.0',
                      '50,', '1000001', 'a,50', ','.join(str(i) for i in range(1, 12))):
            with self.subTest(value=value), self.assertRaises(UserError):
                gift_amounts(value)

    def test_admin_guard_runs_before_accessing_website(self):
        wizard = SimpleNamespace(ensure_one=Mock(), env=SimpleNamespace(is_system=lambda: False, lang='en_US'),
                                 check_access=Mock())
        with self.assertRaises(AccessError):
            AppSetupWizard._admin(wizard)
        wizard.check_access.assert_not_called()

    def test_invalid_origin_or_empty_brand_blocks_continue(self):
        for origin, brand in [('http://example.com', 'Name'), ('https://example.com/odoo', 'Name'),
                              ('https://example.com', '  ')]:
            with self.subTest(origin=origin, brand=brand), self.assertRaises(UserError):
                AppSetupWizard._validate_connect(SimpleNamespace(origin=origin, brand=brand))

    def test_loyalty_presets_reject_invalid_values(self):
        wizard = SimpleNamespace(loyalty_mode='template', _cached_program=lambda kind: False,
            earn_points=1, redeem_points=100, reward_value=10, loyalty_template='percent',
            gift_mode='keep', birthday_mode='keep')
        AppSetupWizard._validate_benefits(wizard)
        for name, value in [('earn_points', 0), ('redeem_points', -1),
                            ('reward_value', 101), ('reward_value', float('nan'))]:
            old = getattr(wizard, name)
            setattr(wizard, name, value)
            with self.subTest(name=name, value=value), self.assertRaises(UserError):
                AppSetupWizard._validate_benefits(wizard)
            setattr(wizard, name, old)

    def test_existing_cached_template_bypasses_new_defaults(self):
        program = object()
        check = Mock()
        wizard = SimpleNamespace(loyalty_mode='template', _cached_program=lambda kind: program,
            _check_programs=check, earn_points=0, redeem_points=0, reward_value=0,
            gift_mode='keep', birthday_mode='keep')
        AppSetupWizard._validate_benefits(wizard)
        check.assert_called_once_with(program, 'loyalty')

    def test_reused_template_is_not_recreated_or_modified(self):
        program = object()
        wizard = SimpleNamespace(_cached_program=lambda kind: program, _check_programs=Mock())
        self.assertIs(AppSetupWizard._create_template(wizard, 'loyalty'), program)

    def test_review_escapes_names_and_text(self):
        wizard = SimpleNamespace(_review_rows=lambda: [('<script>bad</script>', '<img onerror=bad>')])
        AppSetupWizard._compute_review([wizard])
        self.assertNotIn('<script>', wizard.review)
        self.assertNotIn('<img', wizard.review)
        self.assertIn('&lt;script&gt;', wizard.review)
