"""Public onboarding routes; native authentication remains /web/session/authenticate."""

from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, AccessError

from ..models.onboarding import email_value


class AccountController(http.Controller):
    def _scope(self, email=''):
        website = request.website.sudo()
        website._mobile_signup_config()
        # JSON routes do not use Odoo form CSRF. Browser clients must be same-origin.
        origin = request.httprequest.headers.get('Origin')
        expected = website.spx_mobile_account_origin.rstrip('/')
        if origin and origin.rstrip('/') != expected:
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

    @http.route('/spx/mobile/v1/account/forgot', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def forgot(self, email=''):
        website = self._scope()
        email = email_value(email)
        if not request.env['spx.mobile.account.rate'].sudo()._allow(website, '', email):
            raise UserError(_('Too many attempts. Please try again in an hour.'))
        request.env['spx.mobile.registration'].sudo()._forgot(website, email)
        return {'ok': True}

    def _page(self, title, description, form=Markup(''), status=200):
        content = Markup('''<!doctype html><html lang="en"><head><meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/><title>Jenny’s · %s</title>
        <style>@font-face{font-family:Manrope;src:url('/spx_loyalty_mobile/static/src/fonts/manrope-400.ttf')}
        *{box-sizing:border-box}body{margin:0;padding:28px;font-family:Manrope,Arial,sans-serif;background:#f7f8fa;color:#172840}
        main{max-width:480px;margin:40px auto;background:white;padding:32px;border-radius:24px;border:1px solid #e2e6ed}
        h1{font-size:30px;line-height:1.2}p{font-size:14px;line-height:1.8;color:#697386}img{border-radius:50%%}
        label{display:block;font-size:13px;margin:18px 0 8px}input{width:100%%;border:1px solid #dce2eb;border-radius:12px;padding:15px;font-size:16px}
        button{background:#244e9d;color:white;border:0;border-radius:12px;padding:16px;width:100%%;font-size:15px;margin-top:22px;cursor:pointer}
        button:focus-visible,input:focus-visible{outline:3px solid #e5c68c;outline-offset:3px}.brand{letter-spacing:2px;font-size:11px;color:#244e9d}
        </style></head><body><main><img src="/spx_loyalty_mobile/static/description/icon.png" alt="Jenny’s" width="68" height="68"/>
        <p class="brand">JENNY’S ON THE BOULEVARD</p><h1>%s</h1><p>%s</p>%s
        <p style="font-size:11px;margin-top:30px">Good food. Great company. Since 1987.</p></main></body></html>''') % (
            escape(title), escape(title), escape(description), form)
        return request.make_response(content, status=status, headers=[
            ('Content-Type', 'text/html; charset=utf-8'), ('Cache-Control', 'no-store, max-age=0'),
            ('Referrer-Policy', 'no-referrer'), ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy', "default-src 'none'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"),
        ])

    def _link_page(self, kind, token, password=None, confirmation=None):
        try:
            website = self._scope()
            record = request.env['spx.mobile.registration'].sudo()._token(website, token, kind)
            if request.httprequest.method == 'POST':
                if kind == 'reset' and password != confirmation:
                    raise UserError(_('The passwords do not match. Open the email link and try again.'))
                with request.env.cr.savepoint():
                    record._complete(password=password)
                return self._page('Email verified.' if kind == 'signup' else 'Password updated.',
                    'Your account and digital card are ready. Return to Jenny’s app and sign in.' if kind == 'signup'
                    else 'Return to Jenny’s app and sign in with your new password.')
            action = '/spx/mobile/account/verify' if kind == 'signup' else '/spx/mobile/account/reset'
            fields = Markup('''<label for="password">Confirm your password</label><input id="password" name="password" type="password" minlength="12" maxlength="256" required autocomplete="current-password"/><p>Enter the password you chose when creating your account.</p>''') if kind == 'signup' else Markup('''<label for="password">New password</label>
                <input id="password" name="password" type="password" minlength="12" maxlength="256" required autocomplete="new-password"/>
                <label for="confirmation">Confirm new password</label>
                <input id="confirmation" name="confirmation" type="password" minlength="12" maxlength="256" required autocomplete="new-password"/>
                <p>Use at least 12 characters.</p>''')
            form = Markup('''<form method="post" action="%s"><input type="hidden" name="csrf_token" value="%s"/>
                <input type="hidden" name="token" value="%s"/>%s<button type="submit">%s</button></form>''') % (
                action, escape(request.csrf_token()), escape(token), fields,
                'Verify my email' if kind == 'signup' else 'Save new password')
            return self._page('A little welcome. Just for you.' if kind == 'signup' else 'Choose a new password.',
                'Confirm your email to activate your Jenny’s account and digital card.' if kind == 'signup'
                else 'This password will work in the app and on Jenny’s website.', form)
        except (UserError, AccessError) as error:
            return self._page('Let’s try that again.', str(error), status=400)

    @http.route('/spx/mobile/account/verify', type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def verify(self, token='', password=None, **params):
        return self._link_page('signup', token, password=password)

    @http.route('/spx/mobile/account/reset', type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def reset(self, token='', password=None, confirmation=None, **params):
        return self._link_page('reset', token, password, confirmation)
