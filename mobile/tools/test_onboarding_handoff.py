"""Exercise the real handoff service with simulated records; no DB/network."""
from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from odoo import fields
from odoo.exceptions import AccessDenied
from odoo.addons.spx_loyalty_mobile.models.onboarding import MobileRegistration, digest


class TestHandoff(TestCase):
    def setUp(self):
        self.code = 'code-'+'x'*40
        self.receipt = 'receipt-'+'y'*40
        user = Mock(id=42, active=True, share=True)
        user.has_group.return_value = True
        user._mobile_verified_access.return_value = True
        self.record = Mock(id=9, state='done', kind='signup', user_id=user,
            handoff_hash=digest(self.code), receipt_hash=digest(self.receipt),
            handoff_expires_at=fields.Datetime.now()+timedelta(minutes=10))
        self.record.write.side_effect = lambda values: self.record.__dict__.update(values)
        self.service = Mock()
        self.service.sudo.return_value = self.service
        self.service.search.side_effect = lambda domain, **kw: self.record if (
            ('website_id', '=', 15) in domain and self.record.handoff_hash == digest(self.code)) else False

    def call(self, **overrides):
        values = {'website_id': 15, 'code': self.code, 'receipt': self.receipt, 'consume_for': 42}
        values.update(overrides)
        return MobileRegistration._handoff_registration(self.service, **values)

    def test_matching_device_grant_consumes_once(self):
        self.assertIs(self.call(), self.record)
        self.service.env.cr.execute.assert_called_once()
        self.assertFalse(self.record.receipt_hash)
        self.assertFalse(self.record.handoff_hash)
        with self.assertRaises(AccessDenied): self.call()

    def test_wrong_receipt_or_user_or_website_cannot_consume(self):
        for override in [{'receipt': 'wrong-'+'z'*40}, {'consume_for': 99}, {'website_id': 16}]:
            with self.subTest(override=override), self.assertRaises(AccessDenied): self.call(**override)
        self.record.write.assert_not_called()

    def test_expired_grant_and_inactive_user_are_rejected(self):
        self.record.handoff_expires_at = fields.Datetime.now()-timedelta(seconds=1)
        with self.assertRaises(AccessDenied): self.call()
        self.record.handoff_expires_at = fields.Datetime.now()+timedelta(minutes=10)
        self.record.user_id.active = False
        with self.assertRaises(AccessDenied): self.call()
        self.record.write.assert_not_called()

    def test_grant_cannot_be_issued_for_pending_or_reset_record(self):
        for kind, state, receipt in [('signup','pending','hash'), ('reset','done','hash'), ('signup','done',False)]:
            record = Mock(kind=kind, state=state, receipt_hash=receipt)
            self.assertIsNone(MobileRegistration._issue_handoff(record))
            record.write.assert_not_called()
