"""Controller/HTTP regression checks without a running database or mail server.

Uses the connector's actual controller/HTML renderer and Odoo's HTTP dispatcher;
registration persistence and the CSRF validator's result are simulated.
"""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from lxml import html
from werkzeug.exceptions import BadRequest
from werkzeug.wrappers import Response

from odoo.exceptions import AccessError, UserError
from odoo.http import HttpDispatcher
from odoo.addons.spx_loyalty_mobile.controllers import onboarding


TOKEN = 'email-link-' + 'x' * 40


class TestOnboardingLinks(TestCase):
    def setUp(self):
        self.controller = onboarding.AccountController()
        website = Mock(spx_mobile_account_origin='https://jennys.example')
        website.sudo.return_value = website
        self.record = Mock(state='pending')
        self.record._issue_handoff.return_value = 'app-code-'+'y'*40
        self.registrations = Mock()
        self.registrations.sudo.return_value = self.registrations
        self.registrations._token.return_value = self.record
        rate = Mock()
        rate.sudo.return_value = rate
        rate._allow.return_value = True
        env = Mock()
        env.__getitem__ = Mock(side_effect=lambda key: {
            'spx.mobile.registration': self.registrations,
            'spx.mobile.account.rate': rate,
        }[key])
        env.cr.savepoint.return_value = nullcontext()
        self.request = SimpleNamespace(
            website=website, env=env, session=Mock(),
            httprequest=SimpleNamespace(method='GET', headers={}, remote_addr='127.0.0.1'),
            csrf_token=Mock(return_value='csrf-for-this-session'),
            make_response=lambda body, **kwargs: Response(str(body), **kwargs),
        )
        self.addCleanup(patch.stopall)
        patch.object(onboarding, 'request', self.request).start()
        patch.object(onboarding, '_', lambda value: value).start()

    def test_get_renders_password_free_verification_without_activation(self):
        response = self.controller._link_page('signup', TOKEN)
        dom = html.fromstring(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(dom.xpath('//input[@type="password"]'))
        self.assertEqual(dom.xpath('//input[@name="token"]/@value'), [TOKEN])
        self.assertEqual(dom.xpath('//input[@name="csrf_token"]/@value'), ['csrf-for-this-session'])
        self.assertEqual(len(dom.xpath('//form[@id="verify-email-form"]')), 1)
        self.assertIn('verify.js', dom.xpath('//script/@src')[0])
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
        self.record._complete.assert_not_called()
        self.request.session.authenticate.assert_not_called()

    def test_no_referrer_form_origin_can_complete_without_password(self):
        self.request.httprequest.method = 'POST'
        self.request.httprequest.headers = {'Origin': 'null'}
        response = self.controller._link_page('signup', TOKEN, password='ignored-input')
        self.assertEqual(response.status_code, 200)
        self.record._complete.assert_called_once_with(token=TOKEN, password=None)
        self.assertIn('jennys://account/verified?code=', response.get_data(as_text=True))
        self.assertNotIn('receipt=', response.get_data(as_text=True))
        self.request.session.authenticate.assert_not_called()

    def test_known_cross_origin_form_is_rejected(self):
        self.request.httprequest.method = 'POST'
        self.request.httprequest.headers = {'Origin': 'https://unrelated.example'}
        response = self.controller._link_page('signup', TOKEN)
        self.assertEqual(response.status_code, 400)
        self.record._complete.assert_not_called()

    def test_json_null_origin_stays_rejected(self):
        self.request.httprequest.method = 'POST'
        self.request.httprequest.headers = {'Origin': 'null'}
        with self.assertRaises(AccessError):
            self.controller._scope()

    def test_completed_link_only_shows_success(self):
        self.record.state = 'done'
        self.record.receipt_hash = False
        response = self.controller._link_page('signup', TOKEN)
        self.assertIn('Email verified.', response.get_data(as_text=True))
        self.assertNotIn('<form', response.get_data(as_text=True))
        self.record._complete.assert_not_called()

    def test_expired_link_cannot_complete(self):
        self.request.httprequest.method = 'POST'
        self.registrations._token.side_effect = UserError('Request a new email in the app.')
        response = self.controller._link_page('signup', TOKEN)
        self.assertEqual(response.status_code, 400)
        self.record._complete.assert_not_called()

    def test_reset_still_requires_new_password_and_confirmation(self):
        response = self.controller._link_page('reset', TOKEN)
        dom = html.fromstring(response.get_data(as_text=True))
        self.assertEqual(len(dom.xpath('//input[@type="password"]')), 2)
        self.assertTrue(dom.xpath('//script'))
        self.assertEqual(dom.xpath('//input[@name="token"]/@value'), [TOKEN])
        self.request.httprequest.method = 'POST'
        self.request.httprequest.headers = {'Origin': 'null'}
        response = self.controller._link_page('reset', TOKEN, password='one', confirmation='two')
        self.assertEqual(response.status_code, 400)
        self.record._complete.assert_not_called()
        retry = html.fromstring(response.get_data(as_text=True))
        self.assertEqual(retry.xpath('//input[@name="token"]/@value'), [TOKEN])
        self.assertFalse(retry.xpath('//input[@type="password"]/@value'))
        response = self.controller._link_page('reset', TOKEN,
            password='New-password-123!', confirmation='New-password-123!')
        self.assertEqual(response.status_code, 200)
        self.record._complete.assert_called_once_with(token=TOKEN, password='New-password-123!')

    def test_native_dispatcher_blocks_invalid_csrf_before_controller(self):
        for endpoint in (self.controller.verify, self.controller.reset):
            self.assertTrue(endpoint.original_routing['csrf'])
            endpoint = SimpleNamespace(routing=endpoint.original_routing)
            req = SimpleNamespace(
                get_http_params=lambda: {'token': TOKEN, 'csrf_token': 'invalid-csrf'},
                httprequest=SimpleNamespace(method='POST', path='/spx/mobile/account/verify'),
                db='isolated-test', validate_csrf=Mock(return_value=False),
                registry={'ir.http': Mock()},
            )
            with self.assertLogs('odoo.http', level='WARNING'):
                with self.assertRaises(BadRequest):
                    HttpDispatcher.dispatch(SimpleNamespace(request=req), endpoint, {})
            req.validate_csrf.assert_called_once_with('invalid-csrf')
            req.registry['ir.http']._dispatch.assert_not_called()

    def test_reset_errors_name_recovery_action_and_used_link_reports_success(self):
        from odoo.addons.spx_loyalty_mobile.models.onboarding import AccountLinkError
        patch('odoo.addons.spx_loyalty_mobile.models.onboarding._', lambda message: message).start()
        for reason in ('invalid', 'expired', 'replaced', 'used'):
            self.registrations._token.side_effect = AccountLinkError('reset', reason)
            response = self.controller._link_page('reset', TOKEN)
            body = response.get_data(as_text=True)
            self.assertIn('jennys://account/forgot-password', body)
            self.assertNotIn('Request a new email in the app', body)
            self.assertEqual(response.status_code, 200 if reason == 'used' else 400)
            if reason == 'used': self.assertIn('Password already updated.', body)
        self.record._complete.assert_not_called()
