"""Native ORM coverage for template creation, isolation and repeat setup."""
from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

from ..hooks import disconnect_app


@tagged('post_install', '-at_install')
class TestGuidedSetup(TransactionCase):
    def setUp(self):
        super().setUp()
        self.website = self.env['website'].create({
            'name': 'Guided setup', 'company_id': self.env.company.id,
            'domain': 'https://guide.example.invalid',
        })

    def wizard(self, website=None, **values):
        action = (website or self.website).action_mobile_setup_wizard()
        wizard = self.env['spx.mobile.setup.wizard'].browse(action['res_id'])
        wizard.write(values)
        return wizard

    def apply(self, wizard):
        for step in ('benefits', 'customers', 'review'):
            wizard.action_next()
            self.assertEqual(wizard.step, step)
        wizard.confirmed = True
        return wizard.action_apply()

    def counts(self):
        return tuple(self.env[model].search_count([]) for model in (
            'loyalty.program', 'product.product', 'loyalty.card', 'mail.mail', 'pos.order'))

    def test_navigation_does_not_create_business_records_or_write_website(self):
        before = self.counts(), self.website.write_date
        wizard = self.wizard(gift_mode='template', birthday_mode='template')
        wizard.action_next()
        wizard.action_next()
        wizard.action_back()
        wizard.unlink()  # Closing/abandoning a guide never commits its choices.
        self.assertEqual((self.counts(), self.website.write_date), before)
        self.assertFalse(self.website.spx_mobile_enabled)

    def test_creates_native_programs_only_on_apply_and_retries_are_idempotent(self):
        before = self.counts()
        wizard = self.wizard(gift_mode='template', birthday_mode='template', birthday_enabled=True)
        self.apply(wizard)
        self.assertEqual(self.env['loyalty.program'].search_count([]), before[0] + 3)
        self.assertEqual(self.counts()[2:], before[2:])
        loyalty = self.website.spx_mobile_program_ids
        self.assertEqual(loyalty.program_type, 'loyalty')
        self.assertEqual(loyalty.rule_ids.reward_point_mode, 'money')
        self.assertEqual(loyalty.reward_ids.required_points, 100)
        gift = self.website.spx_gift_program_ids
        products = self.website.spx_gift_product_ids
        self.assertEqual(sorted(products.mapped('list_price')), [50, 100, 200])
        self.assertTrue(all(p.is_published and p.website_id == self.website for p in products))
        self.assertEqual(gift.trigger_product_ids.product_tmpl_id, products)
        birthday = self.website.spx_birthday_program_id
        self.assertEqual(len(birthday.rule_ids), 1)
        self.assertFalse(birthday.rule_ids.any_product)
        self.assertFalse(birthday.rule_ids.valid_product_ids)
        self.assertFalse(birthday.trigger_product_ids)
        for program in gift | birthday:
            self.assertTrue(program.mail_template_id)
            self.assertEqual(program.pos_report_print_id, self.env.ref('loyalty.report_gift_card'))
        self.assertNotEqual(birthday, gift)
        for program in loyalty | gift | birthday:
            self.assertEqual(program.website_id, self.website)
            self.assertEqual(program.company_id, self.website.company_id)
            self.assertEqual(program.currency_id, self.website.currency_id)
        after = self.counts()
        wizard.action_apply()
        self.assertEqual(self.counts(), after)

    def test_first_setup_preselects_birthday_but_only_apply_enables_it(self):
        before = self.counts()
        wizard = self.wizard()
        self.assertEqual(wizard.birthday_mode, 'template')
        self.assertTrue(wizard.birthday_enabled)
        self.assertEqual((wizard.birthday_amount, wizard.birthday_days), (50, 21))
        self.assertFalse(self.website.spx_birthday_enabled)
        self.assertEqual(self.counts(), before)
        self.apply(wizard)
        self.assertTrue(self.website.spx_birthday_enabled)
        self.assertEqual(self.website.spx_birthday_program_id.program_type, 'gift_card')
        self.assertFalse(self.website.spx_birthday_program_id.trigger_product_ids)
        self.assertEqual(self.counts()[2:], before[2:], 'Setup must not issue cards or messages')

    def test_reopening_and_reinstall_preserve_birthday_opt_out(self):
        self.apply(self.wizard(birthday_mode='keep', birthday_enabled=False))
        before = self.counts()
        for unused in range(2):
            wizard = self.wizard()
            self.assertEqual(wizard.birthday_mode, 'keep')
            self.assertFalse(wizard.birthday_enabled)
            self.apply(wizard)
            self.assertFalse(self.website.spx_birthday_enabled)
            self.assertFalse(self.website.spx_birthday_program_id)
            self.assertEqual(self.counts(), before)
            disconnect_app(self.env)

    def test_reopen_and_reinstall_reuse_template_and_keep_edited_rules(self):
        first = self.wizard(gift_mode='template', birthday_mode='template')
        self.apply(first)
        program = self.website.spx_mobile_program_ids
        program.reward_ids.discount = 7
        program.rule_ids.reward_point_amount = 2
        original_ids = (program.ids, self.website.spx_gift_program_ids.ids,
                        self.website.spx_birthday_program_id.ids, self.website.spx_gift_product_ids.ids)
        disconnect_app(self.env)
        count = self.counts()
        again = self.wizard(loyalty_mode='template', gift_mode='template', birthday_mode='template', reward_value=99)
        self.apply(again)
        self.assertEqual(self.counts(), count)
        self.assertEqual(program.reward_ids.discount, 7)
        self.assertEqual(program.rule_ids.reward_point_amount, 2)
        self.assertEqual(original_ids, (self.website.spx_mobile_program_ids.ids,
            self.website.spx_gift_program_ids.ids, self.website.spx_birthday_program_id.ids,
            self.website.spx_gift_product_ids.ids))

    def test_existing_programs_keep_native_rules(self):
        program = self.env['loyalty.program'].create({
            'name': 'Admin custom program', 'program_type': 'loyalty',
            'company_id': self.website.company_id.id, 'website_id': self.website.id,
            'currency_id': self.website.currency_id.id,
            'rule_ids': [Command.create({'reward_point_mode': 'money', 'reward_point_amount': 2})],
            'reward_ids': [Command.create({'reward_type': 'discount', 'discount_mode': 'percent',
                                          'discount': 13, 'required_points': 75})],
        })
        self.assertEqual(program.reward_ids.discount, 13)
        self.website.spx_mobile_program_ids = [Command.set(program.ids)]
        wizard = self.wizard()
        self.assertEqual(wizard.loyalty_mode, 'existing')
        before = self.counts()
        self.apply(wizard)
        self.assertEqual(self.counts(), before)
        self.assertEqual(program.reward_ids.discount, 13)

    def test_another_website_gets_its_own_templates(self):
        self.apply(self.wizard())
        other = self.website.copy({'name': 'Second site', 'domain': 'https://second.example.invalid',
                                  'spx_mobile_program_ids': [Command.clear()],
                                  'spx_birthday_program_id': False, 'spx_birthday_enabled': False,
                                  'spx_birthday_amount': 0})
        self.apply(self.wizard(other, loyalty_mode='template'))
        self.assertNotEqual(other.spx_mobile_program_ids, self.website.spx_mobile_program_ids)
        self.assertEqual(other.spx_mobile_program_ids.website_id, other)

    def test_stale_guide_rejects_before_creating_any_records(self):
        wizard = self.wizard(gift_mode='template')
        for unused in range(3):
            wizard.action_next()
        wizard.confirmed = True
        # Two writes in a transaction can share Odoo's transaction timestamp.
        self.website.spx_mobile_brand = 'Other administrator edit'
        wizard.source_revision = 'stale revision'
        before = self.counts()
        with self.assertRaisesRegex(UserError, 'another session'):
            wizard.action_apply()
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.website.spx_mobile_brand, 'Other administrator edit')

    def test_final_confirmation_and_full_validation_cannot_be_skipped(self):
        wizard = self.wizard(step='review')
        with self.assertRaisesRegex(UserError, 'confirm'):
            wizard.action_apply()
        wizard.write({'confirmed': True, 'origin': 'http://unsafe.example'})
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertFalse(self.website.spx_mobile_program_ids)

    def test_signup_requires_approved_policies(self):
        wizard = self.wizard(signup_enabled=True, mail_from='accounts@example.invalid',
                             terms='Terms', privacy='Privacy')
        wizard.action_next()
        wizard.action_next()
        with self.assertRaisesRegex(UserError, 'approved customer policies'):
            wizard.action_next()
        wizard.policies_confirmed = True
        wizard.action_next()
        wizard.confirmed = True
        wizard.action_apply()
        self.assertTrue(self.website.spx_mobile_signup_enabled)
        self.assertEqual(self.website.spx_mobile_signup_program_id, self.website.spx_mobile_program_ids)

    def test_foreign_program_and_archived_template_are_rejected(self):
        self.apply(self.wizard())
        program = self.website.spx_mobile_program_ids
        program.active = False
        wizard = self.wizard(loyalty_mode='template')
        wizard.action_next()
        with self.assertRaisesRegex(UserError, 'must be active'):
            wizard.action_next()
        program.active = True
        other = self.env['website'].create({'name': 'Other', 'company_id': self.env.company.id})
        wizard = self.wizard(other, loyalty_mode='existing', loyalty_program_ids=[Command.set(program.ids)])
        with self.assertRaises(UserError):
            wizard._validate_benefits()

    def test_non_admin_cannot_open_or_apply_guide(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Guide portal test', 'login': 'guide-portal@example.invalid',
            'group_ids': [Command.set(self.env.ref('base.group_portal').ids)],
        })
        with self.assertRaises(AccessError):
            self.website.with_user(user).action_mobile_setup_wizard()
        wizard = self.wizard()
        for method in ('action_next', 'action_back', 'action_apply'):
            with self.assertRaises(AccessError):
                getattr(wizard.with_user(user), method)()
