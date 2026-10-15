"""Database-free account-mail checks; use after Odoo/addon import configuration.

Real SMTP and database permissions are covered by the instance test and native
test_onboarding.py suite. Here mail persistence is simulated and the actual
Odoo send_after_commit callback is exercised with no network connections.
"""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from odoo import SUPERUSER_ID
from odoo.tools.misc import Callbacks
from odoo.addons.mail.models import mail_mail
from odoo.addons.spx_loyalty_mobile.models.onboarding import MobileRegistration


class MailProbe:
    def __init__(self):
        self.ids = [901]
        self.env = SimpleNamespace(cr=SimpleNamespace(dbname='no_database_connection', postcommit=Callbacks()), context={})

    def send_after_commit(self):
        mail_mail.MailMail.send_after_commit(self)


class TestOnboardingMail(TestCase):
    def make_email(self, registration=True):
        mail = MailProbe()
        mail_model = Mock()
        mail_model.with_user.return_value = mail_model
        mail_model.create.return_value = mail
        service = SimpleNamespace(env={'mail.mail': mail_model}, _name='spx.mobile.registration')
        website = SimpleNamespace(spx_mobile_account_origin='https://jennys.example', spx_mobile_mail_from='no-reply@example.com')
        pending = SimpleNamespace(id=27, ensure_one=lambda: None) if registration else None
        MobileRegistration._queue_mail(service, website, 'member@example.com', 'Verify account', 'Welcome', 'Verify your account.',
                                       'https://jennys.example/spx/mobile/account/verify?token=example', registration=pending)
        return mail, mail_model

    def test_mail_created_as_system_and_linked_to_registration(self):
        mail, model = self.make_email()
        model.with_user.assert_called_once_with(SUPERUSER_ID)
        values = model.create.call_args.args[0]
        self.assertEqual((values['model'], values['res_id']), ('spx.mobile.registration', 27))
        self.assertEqual(values['email_to'], 'member@example.com')
        self.assertTrue(values['auto_delete'])

    def test_native_delivery_occurs_only_when_commit_callback_runs(self):
        with patch.object(mail_mail, 'Registry') as registry, patch.object(mail_mail.api, 'Environment') as environment:
            mail, _ = self.make_email()
            registry.assert_not_called()
            cr = SimpleNamespace()
            registry.return_value.cursor.return_value = nullcontext(cr)
            sender = Mock()
            environment.return_value = {'mail.mail': sender}
            mail.env.cr.postcommit.run()
            registry.assert_called_once_with('no_database_connection')
            environment.assert_called_once_with(cr, SUPERUSER_ID, {})
            sender.browse.assert_called_once_with([901])
            sender.browse.return_value.send.assert_called_once_with()

    def test_rollback_discards_native_delivery_callback(self):
        with patch.object(mail_mail, 'Registry') as registry:
            mail, _ = self.make_email()
            mail.env.cr.postcommit.clear()
            mail.env.cr.postcommit.run()
            registry.assert_not_called()

    def test_existing_account_notice_also_uses_postcommit_delivery(self):
        with patch.object(mail_mail, 'Registry') as registry:
            mail, model = self.make_email(registration=False)
            self.assertNotIn('res_id', model.create.call_args.args[0])
            registry.return_value.cursor.return_value = nullcontext(SimpleNamespace())
            with patch.object(mail_mail.api, 'Environment', return_value={'mail.mail': Mock()}):
                mail.env.cr.postcommit.run()
            registry.assert_called_once()

    def test_migration_only_links_matching_preexisting_registration_mails(self):
        def make_mail(**overrides):
            obj = SimpleNamespace(model=False, res_id=False, email_to='member@example.com', **overrides)
            obj.write = Mock(side_effect=lambda values: obj.__dict__.update(values))
            return obj
        linked = make_mail()
        wrong_recipient = make_mail()
        wrong_recipient.email_to = 'someone.else@example.com'
        other_model = make_mail()
        other_model.model, other_model.res_id = 'sale.order', 8
        registrations = [SimpleNamespace(id=i+1, email='member@example.com', mail_id=mail)
                         for i, mail in enumerate((linked, wrong_recipient, other_model))]
        service = Mock(_name='spx.mobile.registration')
        service.sudo.return_value = service
        service.search.return_value = registrations
        MobileRegistration._repair_account_mail_links(service)
        MobileRegistration._repair_account_mail_links(service)
        linked.write.assert_called_once_with({'model': 'spx.mobile.registration', 'res_id': 1})
        wrong_recipient.write.assert_not_called()
        other_model.write.assert_not_called()
