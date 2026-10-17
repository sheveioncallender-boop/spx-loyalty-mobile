"""Recovery regressions using real service/authentication code and simulated rows."""
from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from odoo import fields
from odoo.exceptions import AccessDenied
from odoo.addons.base.models.res_users import ResUsers
from odoo.addons.spx_loyalty_mobile.models import onboarding as model


class PasswordRows:
    """A tiny cursor for native password read/write, with real Odoo hashing."""
    def __init__(self, hashed):
        self.hashed = hashed
    def execute(self, query, params=None):
        if query.startswith('UPDATE res_users SET password='):
            self.hashed = params[0]
        elif not query.startswith('SELECT COALESCE(password'):
            raise AssertionError('Unexpected native password query')
    def fetchone(self):
        return [self.hashed]


class TestRecovery(TestCase):
    def setUp(self):
        patcher = patch.object(model, '_', lambda message: message)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.now = fields.Datetime.now()
        self.token = 'reset-'+'x'*40
        self.website = Mock(id=15, spx_mobile_account_origin='https://jennys.example')
        self.record = Mock(id=9, kind='reset', state='pending', email='member@example.com',
                           token_hash=model.digest(self.token), website_id=self.website,
                           expires_at=self.now+timedelta(hours=24))
        self.record.write.side_effect = lambda vals: self.record.__dict__.update(vals)
        self.service = Mock()
        self.service.sudo.return_value = self.service
        self.service.search.side_effect = lambda domain, **kw: self.record if (
            ('website_id', '=', 15) in domain and ('kind', '=', 'reset') in domain
            and ('token_hash', '=', self.record.token_hash) in domain) else False

    def lookup(self, token=None):
        return model.MobileRegistration._token(self.service, self.website, token or self.token, 'reset')

    def test_fresh_reset_survives_previous_one_hour_limit(self):
        with patch.object(fields.Datetime, 'now', return_value=self.now+timedelta(minutes=90)):
            self.assertIs(self.lookup(), self.record)
        with patch.object(fields.Datetime, 'now', return_value=self.now+timedelta(hours=24, seconds=1)):
            with self.assertRaises(model.AccountLinkError) as error: self.lookup()
            self.assertEqual(error.exception.reason, 'expired')

    def test_used_replaced_and_invalid_links_have_distinct_recovery_messages(self):
        for state, reason in [('done','used'), ('expired','replaced')]:
            self.record.state = state
            with self.assertRaises(model.AccountLinkError) as error: self.lookup()
            self.assertEqual(error.exception.reason, reason)
            self.assertIn('password reset', str(error.exception))
        with self.assertRaises(model.AccountLinkError) as error: self.lookup('wrong-'+'y'*40)
        self.assertEqual(error.exception.reason, 'invalid')

    def test_issued_reset_has_24_hour_expiry_and_email_matches(self):
        self.record._queue_mail.return_value = Mock()
        with patch.object(fields.Datetime, 'now', return_value=self.now):
            model.MobileRegistration._send_link(self.record)
        self.assertEqual(self.record.expires_at, self.now+timedelta(hours=24))
        self.assertIn('24 hours', self.record._queue_mail.call_args.args[4])

    def test_duplicate_signup_raises_before_email_or_registration(self):
        values = dict(first_name='Alex', last_name='Joseph', phone='5550123',
                      email='Member@Example.com', password='Long-password-123!',
                      birthday='1990-01-01', terms=True, policy_version='1')
        self.website.spx_mobile_policy_version = '1'
        self.service._users.return_value = Mock(id=42)
        with self.assertRaises(model.AccountExistsUserError):
            model.MobileRegistration._signup(self.service, self.website, values)
        self.service._users.assert_called_once_with('member@example.com')
        self.service.create.assert_not_called()
        self.service._queue_mail.assert_not_called()

    def test_completed_reset_uses_native_hashing_and_rejects_old_password(self):
        old, new = 'Original-password-123!', 'Replacement-password-456!'
        # Actual Odoo crypt context, setter and credential checker; cursor rows simulated.
        config = Mock()
        config.sudo.return_value = config
        config.get_param.return_value = 0
        context_owner = SimpleNamespace(env={'ir.config_parameter': config})
        crypto = ResUsers._crypt_context.__wrapped__(context_owner)
        cursor = PasswordRows(crypto.hash(old))
        user = Mock(id=42, active=True, share=True, email=self.record.email)
        user.env = SimpleNamespace(cr=cursor, user=user)
        user._crypt_context.return_value = crypto
        user._set_encrypted_password.side_effect = lambda uid, hashed: ResUsers._set_encrypted_password(user, uid, hashed)
        user.with_context.return_value = user
        def write(values):
            user.password = values['password']
            group = Mock()
            group.__iter__ = Mock(return_value=iter([user]))
            group._crypt_context.return_value = crypto
            group._set_encrypted_password.side_effect = user._set_encrypted_password
            ResUsers._set_password(group)
        user.write.side_effect = write
        self.record.user_id = user
        self.record.sudo.return_value = self.record
        # Before recovery the original password authenticates.
        self.assertEqual(ResUsers._check_credentials(user, {'type':'password','password':old}, {'interactive':True})['uid'], 42)
        model.MobileRegistration._complete(self.record, self.token, new)
        self.assertEqual(self.record.state, 'done')
        self.assertEqual(ResUsers._check_credentials(user, {'type':'password','password':new}, {'interactive':True})['uid'], 42)
        with self.assertRaises(AccessDenied):
            ResUsers._check_credentials(user, {'type':'password','password':old}, {'interactive':True})
        # Replay is informational only; cannot install another password.
        with self.assertRaises(model.AccountLinkError) as error:
            model.MobileRegistration._complete(self.record, self.token, 'Replay-password-789!')
        self.assertEqual(error.exception.reason, 'used')
        user.write.assert_called_once()
        self.record.search.return_value.write.assert_called_once_with({
            'handoff_hash':False, 'handoff_expires_at':False, 'receipt_hash':False})
