"""Public onboarding routes; native authentication remains /web/session/authenticate."""

from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, AccessError, AccessDenied
from urllib.parse import urlencode

from ..models.onboarding import email_value, digest


class AccountController(http.Controller):
    def _scope(self, email='', *, browser_form=False, registration=True):
        website = request.website.sudo()
        if registration:
            website._mobile_signup_config()
        elif not website.spx_mobile_enabled:
            raise AccessError(_('This request is unavailable.'))
        # JSON routes do not use Odoo form CSRF. Browser clients must be same-origin.
        # A no-referrer page can submit an HTML form with Origin: null. Only
        # the HTTP form routes below may accept that case: native Odoo CSRF
        # validation has already run before their controller is invoked.
        origin = request.httprequest.headers.get('Origin')
        expected = (website.spx_mobile_account_origin or request.httprequest.host_url).rstrip('/')
        opaque_form = browser_form and request.httprequest.method == 'POST' and origin == 'null'
        if origin and origin.rstrip('/') != expected and not opaque_form:
            raise AccessError(_('This request is unavailable.'))
        ip = request.httprequest.remote_addr or 'unknown'
        if not request.env['spx.mobile.account.rate'].sudo()._allow(website, ip, email):
            raise UserError(_('Too many attempts. Please try again in an hour.'))
        return website

    @http.route('/spx/mobile/v1/account/config', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def config(self):
        website = request.website.sudo()
        try:
            website._mobile_signup_config()
        except UserError:
            return {'enabled': False}
        return {'enabled': True, 'terms': website.spx_mobile_terms, 'privacy': website.spx_mobile_privacy,
                'policy_version': website.spx_mobile_policy_version}

    @http.route('/spx/mobile/v1/account/signup', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def signup(self, **values):
        # Consume IP quota even for malformed email. Email quota then spans all account actions.
        website = self._scope()
        email = email_value(values.get('email'))
        if not request.env['spx.mobile.account.rate'].sudo()._allow(website, '', email):
            raise UserError(_('Too many attempts. Please try again in an hour.'))
        receipt = request.env['spx.mobile.registration'].sudo()._signup(website, values)
        return {'ok': True, 'receipt': receipt}

    @http.route('/spx/mobile/v1/account/resend', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def resend(self, receipt=''):
        website = self._scope()
        request.env['spx.mobile.registration'].sudo()._resend(website, receipt)
        return {'ok': True}

    @http.route('/spx/mobile/v1/account/status', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def status(self, receipt=''):
        website = self._scope()
        if not isinstance(receipt, str) or not 30 <= len(receipt) <= 100:
            return {'verified': False}
        record = request.env['spx.mobile.registration'].sudo().search([
            ('website_id', '=', website.id), ('receipt_hash', '=', digest(receipt)),
            ('kind', '=', 'signup'), ('state', '=', 'done')], limit=1)
        return {'verified': bool(record and record.user_id.active and record.user_id.share
            and record.user_id._mobile_verified_access())}

    @http.route('/spx/mobile/v1/account/forgot', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def forgot(self, email=''):
        website = self._scope()
        email = email_value(email)
        if not request.env['spx.mobile.account.rate'].sudo()._allow(website, '', email):
            raise UserError(_('Too many attempts. Please try again in an hour.'))
        request.env['spx.mobile.registration'].sudo()._forgot(website, email)
        return {'ok': True}

    @http.route('/spx/mobile/v1/account/signin', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def signin(self, email='', password=''):
        self._scope(registration=False)
        user = request.env['spx.mobile.registration'].sudo()._users(email_value(email))
        if len(user) != 1 or not user.active or not user.share or not user.has_group('base.group_portal'):
            raise AccessDenied()
        # Resolve the customer's email to the existing native login. Never
        # create another user just because that login has a different value.
        auth = request.session.authenticate(request.env, {
            'type': 'password', 'login': user.login, 'password': password,
        })
        if auth['uid'] != request.session.uid:
            return {'uid': None}
        request.session.db = request.db
        request._save_session(request.env)
        return {'uid': auth['uid']}

    @http.route('/spx/mobile/v1/account/exchange', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def exchange(self, code='', receipt=''):
        website = self._scope()
        service = request.env['spx.mobile.registration'].sudo()
        try:
            record = service._handoff_registration(website.id, code, receipt)
            auth = request.session.authenticate(request.env, {
                'type': 'spx_mobile_handoff', 'login': record.user_id.login,
                'website_id': website.id, 'code': code, 'receipt': receipt,
            })
        except AccessDenied:
            raise UserError(_('This automatic sign-in link has expired or belongs to another device. Please sign in with your email and password.')) from None
        if auth['uid'] != request.session.uid:
            # Do not bypass a native second factor.
            raise UserError(_('Please sign in to complete your account’s additional security step.'))
        request.session.db = request.db
        request._save_session(request.env)
        return {'uid': auth['uid']}

    def _success(self, kind, record):
        code = record._issue_handoff() if kind == 'signup' else None
        path = 'verified' if kind == 'signup' else 'password-updated'
        uri = 'jennys://account/' + path + ('?' + urlencode({'code': code}) if code else '')
        button = Markup('<a class="app-button" id="open-jennys-app" href="%s">Open Jenny’s</a>') % escape(uri)
        return self._page('Email verified.' if kind == 'signup' else 'Password updated.',
            'Your account and digital card are ready. We’re opening Jenny’s. If it doesn’t open, tap below. On another device, sign in using your original email and password.' if kind == 'signup'
            else 'Your new password is saved. Open Jenny’s and sign in with it.', button, verify_script=True)

    def _page(self, title, description, form=Markup(''), status=200, *, verify_script=False):
        content = Markup('''<!doctype html><html lang="en"><head><meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/><title>Jenny’s · %s</title>
        <style>@font-face{font-family:Manrope;src:url('/spx_loyalty_mobile/static/src/fonts/manrope-400.ttf')}
        *{box-sizing:border-box}body{margin:0;padding:28px;font-family:Manrope,Arial,sans-serif;background:#f7f8fa;color:#172840}
        main{max-width:480px;margin:40px auto;background:white;padding:32px;border-radius:24px;border:1px solid #e2e6ed}
        h1{font-size:30px;line-height:1.2}p{font-size:14px;line-height:1.8;color:#697386}img{border-radius:50%%}
        label{display:block;font-size:13px;margin:18px 0 8px}input{width:100%%;border:1px solid #dce2eb;border-radius:12px;padding:15px;font-size:16px}
        button{background:#244e9d;color:white;border:0;border-radius:12px;padding:16px;width:100%%;font-size:15px;margin-top:22px;cursor:pointer}
        .app-button{display:block;background:#244e9d;color:white;border-radius:12px;padding:16px;text-align:center;text-decoration:none;margin-top:24px;font-size:15px}
        button:focus-visible,input:focus-visible{outline:3px solid #e5c68c;outline-offset:3px}.brand{letter-spacing:2px;font-size:11px;color:#244e9d}
        .verification-status{display:flex;align-items:center;gap:12px;margin:24px 0;color:#244e9d;font-size:14px}
        [hidden]{display:none!important}.spinner{width:20px;height:20px;flex-shrink:0;border:2px solid #e2e6ed;border-top-color:#244e9d;border-radius:50%%;animation:spin .8s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.spinner{animation:none}}
        @media(max-width:520px){body{padding:20px}main{margin:24px auto;padding:26px}h1{font-size:28px}}
        </style></head><body><main><img src="/spx_loyalty_mobile/static/description/icon.png" alt="Jenny’s" width="68" height="68"/>
        <p class="brand">JENNY’S ON THE BOULEVARD</p><h1>%s</h1><p>%s</p>%s
        <p style="font-size:11px;margin-top:30px">Good food. Great company. Since 1987.</p></main>%s</body></html>''') % (
            escape(title), escape(title), escape(description), form,
            Markup('<script src="/spx_loyalty_mobile/static/src/account/verify.js?v=19.0.3.0.3" defer></script>') if verify_script else Markup(''))
        return request.make_response(content, status=status, headers=[
            ('Content-Type', 'text/html; charset=utf-8'), ('Cache-Control', 'no-store, max-age=0'),
            ('Referrer-Policy', 'no-referrer'), ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"),
        ])

    def _link_page(self, kind, token, password=None, confirmation=None):
        try:
            website = self._scope(browser_form=True)
            record = request.env['spx.mobile.registration'].sudo()._token(website, token, kind)
            if kind == 'signup' and record.state == 'done' and not record.receipt_hash:
                return self._page('Email verified.',
                    'Your account is ready. Open Jenny’s to continue or sign in.',
                    Markup('<a class="app-button" id="open-jennys-app" href="jennys://account/verified">Open Jenny’s</a>'), verify_script=True)
            if request.httprequest.method == 'POST':
                if kind == 'reset' and password != confirmation:
                    raise UserError(_('The passwords do not match. Open the email link and try again.'))
                with request.env.cr.savepoint():
                    record._complete(token=token, password=password if kind == 'reset' else None)
                return self._success(kind, record)
            action = '/spx/mobile/account/verify' if kind == 'signup' else '/spx/mobile/account/reset'
            fields = Markup('') if kind == 'signup' else Markup('''<label for="password">New password</label>
                <input id="password" name="password" type="password" minlength="12" maxlength="256" required autocomplete="new-password"/>
                <label for="confirmation">Confirm new password</label>
                <input id="confirmation" name="confirmation" type="password" minlength="12" maxlength="256" required autocomplete="new-password"/>
                <p>Use at least 12 characters.</p>''')
            form = Markup('''<form id="%s" method="post" action="%s"><input type="hidden" name="csrf_token" value="%s"/>
                <input type="hidden" name="token" value="%s"/>%s<button type="submit">%s</button></form>''') % (
                'verify-email-form' if kind == 'signup' else 'reset-password-form', action, escape(request.csrf_token()), escape(token), fields,
                'Verify my email' if kind == 'signup' else 'Save new password')
            if kind == 'signup':
                form = Markup('''<div id="verification-status" class="verification-status" role="status" aria-live="polite" hidden>
                    <span class="spinner" aria-hidden="true"></span><span>Verifying your email…</span></div>''') + form
            return self._page('A little welcome. Just for you.' if kind == 'signup' else 'Choose a new password.',
                'Your email will be verified automatically. If it does not continue, tap Verify my email below.' if kind == 'signup'
                else 'This password will work in the app and on Jenny’s website.', form, verify_script=kind == 'signup')
        except (UserError, AccessError) as error:
            return self._page('Let’s try that again.', str(error), status=400)

    @http.route('/spx/mobile/account/verify', type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=True, sitemap=False)
    def verify(self, token='', password=None, **params):
        return self._link_page('signup', token, password=password)

    @http.route('/spx/mobile/account/reset', type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=True, sitemap=False)
    def reset(self, token='', password=None, confirmation=None, **params):
        return self._link_page('reset', token, password, confirmation)
