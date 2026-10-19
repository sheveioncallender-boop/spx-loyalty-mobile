"""Run on a disposable Odoo 19 database before approving live deployment."""
import base64
import json
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

from ..hooks import disconnect_app
from ..models.lifecycle import connection_origin


@tagged('post_install', '-at_install')
class TestLifecycle(TransactionCase):
    def test_retention_is_default_and_only_opens_native_preview(self):
        wizard = self.env['spx.mobile.removal'].create({})
        self.assertEqual(wizard.mode, 'keep')
        module = self.env['ir.module.module'].search([('name', '=', 'spx_loyalty_mobile')])
        self.assertEqual(wizard.action_continue()['context']['default_module_ids'], module.ids)
        self.assertNotEqual(module.state, 'to remove')

    def test_remove_requires_explicit_confirmation(self):
        wizard = self.env['spx.mobile.removal'].create({'mode': 'remove'})
        with self.assertRaises(UserError):
            wizard.action_continue()
        wizard.confirm_remove = True
        data = self.env['ir.module.module'].search([('name', '=', 'spx_loyalty_mobile_data')])
        self.assertEqual(wizard.action_continue()['context']['default_module_ids'], data.ids)
        self.assertNotEqual(data.state, 'to remove')

    def test_customer_cannot_remove_or_configure(self):
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Lifecycle portal test', 'login': 'lifecycle@example.invalid',
            'group_ids': [Command.set(self.env.ref('base.group_portal').ids)],
        })
        for model in ('spx.mobile.removal', 'spx.mobile.connection'):
            with self.assertRaises(AccessError):
                self.env[model].with_user(user).create({})
        wizard = self.env['spx.mobile.removal'].create({})
        with self.assertRaises(AccessError):
            wizard.with_user(user).action_continue()

    def test_connection_file_contains_no_credentials(self):
        website = self.env['website'].search([], limit=1)
        record = self.env['spx.mobile.connection'].create({
            'website_id': website.id, 'origin': 'https://jennys.example/',
        })
        payload = json.loads(base64.b64decode(record.config_file))
        self.assertEqual(payload, {
            'JENNYS_API_URL': 'https://jennys.example', 'JENNYS_DATABASE': self.env.cr.dbname,
        })
        self.assertEqual(record.database, self.env.cr.dbname)

    def test_rejects_non_origin_and_credentials(self):
        for value in ('http://example.com', 'https://user:secret@example.com',
                      'https://example.com/odoo', 'https://example.com?key=123',
                      'https://example.com/#other', 'https://bad host',
                      'https://example.com:999999', 'https://example.com\\other'):
            with self.subTest(value=value), self.assertRaises(UserError):
                connection_origin(value)

    def test_disconnect_keeps_native_records_and_history(self):
        website = self.env['website'].search([], limit=1)
        partner = self.env['res.partner'].create({
            'name': 'Retention test', 'spx_mobile_birthday': '1990-01-01',
            'spx_mobile_policy_version': 'retention-test',
        })
        program = self.env['loyalty.program'].create({'name': 'Retained native points', 'program_type': 'loyalty'})
        card = self.env['loyalty.card'].with_context(loyalty_no_mail=True).create({
            'partner_id': partner.id, 'program_id': program.id, 'points': 65,
        })
        message = self.env['spx.mobile.message'].create({
            'website_id': website.id, 'partner_id': partner.id, 'name': 'Retained', 'body': 'History',
        })
        pending = self.env['spx.mobile.registration'].sudo().create({
            'website_id': website.id, 'email': 'retention@example.invalid', 'kind': 'signup',
            'expires_at': fields.Datetime.now(), 'token_hash': 'test-token',
            'password_hash': 'test-hash', 'handoff_hash': 'test-handoff',
        })
        before = (partner.id, card.id, card.code, card.points, message.id)
        disconnect_app(self.env)
        self.assertEqual(before, (partner.id, card.id, card.code, card.points, message.id))
        self.assertTrue(partner.exists() and card.exists() and message.exists())
        self.assertEqual(str(partner.spx_mobile_birthday), '1990-01-01')
        self.assertEqual(partner.spx_mobile_policy_version, 'retention-test')
        self.assertEqual(pending.state, 'expired')
        self.assertFalse(pending.token_hash or pending.password_hash or pending.handoff_hash)
