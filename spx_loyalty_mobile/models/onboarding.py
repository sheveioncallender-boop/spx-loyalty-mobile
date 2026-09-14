"""Verified onboarding boundary; native users, password hashing and loyalty cards.

Pending registrations are not users and cannot authenticate through any Odoo API.
Every mutating service is private and is called by the scoped HTTP controller only.
"""
import hashlib
import re
import secrets
import time
from datetime import timedelta
from urllib.parse import urlparse

from markupsafe import Markup, escape

from odoo import api, fields, models, Command, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, AccessDenied
from odoo.tools import email_normalize, escape_psql


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def email_value(value):
    if not isinstance(value, str) or len(value) > 254:
        raise UserError(_('Enter a valid email address.'))
    normalized = email_normalize(value.strip())
    if not normalized or normalized.casefold() != value.strip().casefold():
        raise UserError(_('Enter a valid email address.'))
    return normalized.casefold()


def password_value(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256:
        raise UserError(_('Use a password between 12 and 256 characters.'))
    return value


class Website(models.Model):
    _inherit = 'website'

    # Keep signup-only columns out of unrelated website reads while new code is
    # deployed but its module upgrade is pending. Explicit reads still require
    # the real schema; this does not provide fallback values or skip migration.
    spx_mobile_signup_enabled = fields.Boolean('Enable verified signup', groups='base.group_system', prefetch=False)
    spx_mobile_signup_program_id = fields.Many2one('loyalty.program', string='New member loyalty program', groups='base.group_system', prefetch=False)
    spx_mobile_mail_from = fields.Char('Account email sender', default='no-reply@spxcorp.site', groups='base.group_system', prefetch=False)
    spx_mobile_account_origin = fields.Char('Account link origin', groups='base.group_system', prefetch=False, help='HTTPS origin only, for example https://jennys.spxcorp.site. Verification and recovery pages are served here.')
    spx_mobile_terms = fields.Text('Account and rewards terms', groups='base.group_system', prefetch=False)
    spx_mobile_privacy = fields.Text('Privacy policy', groups='base.group_system', prefetch=False)
    spx_mobile_policy_version = fields.Char('Policy version', default='1', groups='base.group_system', prefetch=False)

    def _mobile_signup_config(self):
        self.ensure_one()
        p = self.spx_mobile_signup_program_id
        origin = (self.spx_mobile_account_origin or '').rstrip('/')
        uri = urlparse(origin)
        if (not self.spx_mobile_enabled or not self.spx_mobile_signup_enabled or not p
                or not p.active or p.program_type != 'loyalty'
                or p not in self.spx_mobile_program_ids
                or (p.company_id and p.company_id != self.company_id)
                or (p.website_id and p.website_id != self)
                or not self.spx_mobile_terms or not self.spx_mobile_privacy
                or not self.spx_mobile_policy_version or not self.spx_mobile_mail_from
                or uri.scheme != 'https' or not uri.hostname or uri.path
                or uri.query or uri.fragment or uri.username or uri.password):
            raise UserError(_('Joining is temporarily unavailable. Please contact Jenny’s or try again later.'))
        email_value(self.spx_mobile_mail_from)
        return origin

    @api.constrains('spx_mobile_signup_enabled', 'spx_mobile_signup_program_id', 'spx_mobile_program_ids',
                    'spx_mobile_mail_from', 'spx_mobile_account_origin', 'spx_mobile_terms', 'spx_mobile_privacy',
                    'spx_mobile_policy_version')
    def _check_mobile_signup_config(self):
        for w in self.filtered('spx_mobile_signup_enabled'):
            try:
                w._mobile_signup_config()
            except UserError as e:
                raise ValidationError(_('Complete the signup program, visible programs, HTTPS account origin, sender, terms, privacy and policy version before enabling signup.')) from e


class Users(models.Model):
    _inherit = 'res.users'

    # User prefetch is used by backend actions, login and Discuss. New optional
    # signup columns must not make those native reads depend on signup's schema.
    spx_mobile_verified_email = fields.Char('Verified app email', readonly=True, copy=False, groups='base.group_system', prefetch=False)
    spx_mobile_legacy_access = fields.Boolean('Existing member access', readonly=True, copy=False, groups='base.group_system', prefetch=False,
        help='Preserves access for portal accounts that already existed when verified signup was installed.')

    def _mobile_verified_access(self):
        self.ensure_one()
        user = self.sudo()
        return bool(user.spx_mobile_legacy_access or (user.spx_mobile_verified_email
            and user.spx_mobile_verified_email == email_value(user.email or '')
            and user.spx_mobile_verified_email == email_value(user.login or '')))

    def _check_credentials(self, credential, env):
        if credential.get('type') != 'spx_mobile_handoff':
            return super()._check_credentials(credential, env)
        self.ensure_one()
        self.env['spx.mobile.registration'].sudo()._handoff_registration(
            credential.get('website_id'), credential.get('code'), credential.get('receipt'),
            consume_for=self.id)
        # Keep native session rotation, login tracking and MFA handling.
        return {'uid': self.id, 'auth_method': 'spx_mobile_handoff', 'mfa': 'default'}


class Partner(models.Model):
    _inherit = 'res.partner'

    # res.users.name delegates to the partner; protect that native lookup too.
    spx_mobile_first_name = fields.Char('App first name', groups='base.group_system', prefetch=False)
    spx_mobile_last_name = fields.Char('App last name', groups='base.group_system', prefetch=False)
    spx_mobile_birthday = fields.Date('Birthday', groups='base.group_system', prefetch=False)
    spx_mobile_sms = fields.Boolean('App promotional SMS', groups='base.group_system', prefetch=False)
    spx_mobile_verified_at = fields.Datetime('App email verified', readonly=True, groups='base.group_system', prefetch=False)
    spx_mobile_policy_version = fields.Char('Accepted policy version', readonly=True, groups='base.group_system', prefetch=False)
    spx_mobile_terms_at = fields.Datetime('Terms accepted', readonly=True, groups='base.group_system', prefetch=False)


class MobileRate(models.Model):
    _name = 'spx.mobile.account.rate'
    _description = 'Account request rate limits'
    key = fields.Char(required=True, index=True)
    bucket = fields.Integer(required=True)
    count = fields.Integer(default=0)
    _key_unique = models.Constraint('UNIQUE(key, bucket)', 'Unique request bucket.')

    @api.model
    def _allow(self, website, ip, email=''):
        # Independent transaction: failed requests must also consume their limit.
        bucket = int(time.time() // 3600)
        keys = [(f'ip:{website.id}:{ip}', 40)] if ip else []
        if email:
            keys.append((f'email:{website.id}:{email}', 8))
        allowed = True
        with self.env.registry.cursor() as cr:
            for key, limit in keys:
                cr.execute('''INSERT INTO spx_mobile_account_rate (key,bucket,count)
                    VALUES (%s,%s,1) ON CONFLICT (key,bucket)
                    DO UPDATE SET count=spx_mobile_account_rate.count+1 RETURNING count''', (digest(key), bucket))
                allowed = cr.fetchone()[0] <= limit and allowed
            cr.commit()
        return allowed

    @api.autovacuum
    def _gc(self):
        self.sudo().search([('bucket', '<', int(time.time() // 3600) - 48)]).unlink()


class MobileRegistration(models.Model):
    _name = 'spx.mobile.registration'
    _description = 'Jenny’s account registration and recovery'
    _rec_name = 'email'
    _order = 'create_date desc, id desc'

    website_id = fields.Many2one('website', required=True, ondelete='cascade', index=True)
    email = fields.Char(required=True, index=True)
    kind = fields.Selection([('signup', 'Signup'), ('reset', 'Password reset')], required=True)
    state = fields.Selection([('pending', 'Awaiting email'), ('done', 'Completed'), ('expired', 'Expired')], default='pending', required=True)
    first_name = fields.Char()
    last_name = fields.Char()
    phone = fields.Char()
    birthday = fields.Date()
    city = fields.Char()
    marketing_email = fields.Boolean()
    marketing_sms = fields.Boolean()
    policy_version = fields.Char()
    terms_at = fields.Datetime()
    password_hash = fields.Char(copy=False, groups='base.group_system')
    token_hash = fields.Char(index=True, copy=False, groups='base.group_system')
    receipt_hash = fields.Char(index=True, copy=False, groups='base.group_system')
    expires_at = fields.Datetime(required=True)
    sent_at = fields.Datetime()
    verified_at = fields.Datetime()
    user_id = fields.Many2one('res.users', readonly=True, ondelete='set null')
    partner_id = fields.Many2one('res.partner', readonly=True, ondelete='set null')
    card_id = fields.Many2one('loyalty.card', readonly=True, ondelete='set null')
    mail_id = fields.Many2one('mail.mail', readonly=True, ondelete='set null')
    handoff_hash = fields.Char(copy=False, index=True, groups='base.group_system', prefetch=False)
    handoff_expires_at = fields.Datetime(copy=False, groups='base.group_system', prefetch=False)

    def _issue_handoff(self):
        self.ensure_one()
        if self.kind != 'signup' or self.state != 'done' or not self.receipt_hash:
            return None
        code = secrets.token_urlsafe(32)
        self.write({'handoff_hash': digest(code),
                    'handoff_expires_at': fields.Datetime.now()+timedelta(minutes=10)})
        return code

    @api.model
    def _handoff_registration(self, website_id, code, receipt, *, consume_for=None):
        if (not isinstance(website_id, int) or isinstance(website_id, bool)
                or any(not isinstance(value, str) or not 30 <= len(value) <= 100 for value in (code, receipt))):
            raise AccessDenied()
        record = self.sudo().search([('website_id', '=', website_id), ('handoff_hash', '=', digest(code)),
                                    ('kind', '=', 'signup'), ('state', '=', 'done')], limit=1)
        if not record:
            raise AccessDenied()
        if consume_for is not None:
            self.env.cr.execute('SELECT id FROM spx_mobile_registration WHERE id=%s FOR UPDATE', (record.id,))
            record.invalidate_recordset()
        user = record.user_id
        if (not secrets.compare_digest(record.handoff_hash or '', digest(code))
                or not secrets.compare_digest(record.receipt_hash or '', digest(receipt))
                or not record.handoff_expires_at or record.handoff_expires_at <= fields.Datetime.now()
                or record.state != 'done' or not user or not user.active or not user.share
                or not user.has_group('base.group_portal') or not user._mobile_verified_access()
                or (consume_for is not None and user.id != consume_for)):
            raise AccessDenied()
        record.website_id._mobile_signup_config()
        if consume_for is not None:
            record.write({'handoff_hash': False, 'handoff_expires_at': False, 'receipt_hash': False})
        return record

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        # Registration records remain read-only for administrators. Permit them
        # to maintain the native messages linked to records they can read, so
        # mail.mail can write its delegated Message-Id after SMTP succeeds.
        # Other users and message operations retain Odoo's normal checks.
        if message_operation == 'write' and self.env.user.has_group('base.group_system'):
            return dict.fromkeys(self, 'read')
        return super()._mail_get_operation_for_mail_message_operation(message_operation)

    @api.model
    def _repair_account_mail_links(self):
        # Upgrade only mails already referenced by a registration. Do not infer
        # ownership from subjects, send emails, or touch unrelated system mail.
        registrations = self.sudo().search([('mail_id', '!=', False)])
        for registration in registrations:
            mail = registration.mail_id
            if (not mail.model and not mail.res_id
                    and (mail.email_to or '').strip().casefold() == registration.email.casefold()):
                mail.write({'model': self._name, 'res_id': registration.id})

    @api.model
    def _users(self, email):
        return self.env['res.users'].sudo().with_context(active_test=False).search([
            '|', '|', ('login', '=ilike', escape_psql(email)), ('email', '=ilike', escape_psql(email)),
            ('partner_id.email_normalized', '=ilike', escape_psql(email))])

    @api.model
    def _lock_email(self, email):
        # Stable lock across workers and websites. Native login uniqueness is also enforced.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s)', (int(digest(email)[:15], 16),))

    @api.model
    def _signup(self, website, values):
        website._mobile_signup_config()
        if not isinstance(values, dict):
            raise UserError(_('Check the signup details and try again.'))
        email = email_value(values.get('email'))
        pw = password_value(values.get('password'))
        first = values.get('first_name')
        last = values.get('last_name')
        if any(not isinstance(v, str) or not v.strip() or len(v.strip()) > 80 for v in (first, last)):
            raise UserError(_('Enter your first and last name.'))
        phone = values.get('phone')
        if not isinstance(phone, str) or not re.fullmatch(r'[0-9]{3} ?[0-9]{4}', phone):
            raise UserError(_('Enter a seven-digit phone number after +1 (868).'))
        try:
            dob = fields.Date.to_date(values.get('birthday'))
            if not dob or dob < fields.Date.to_date('1900-01-01') or dob > fields.Date.today():
                raise ValueError()
        except (TypeError, ValueError):
            raise UserError(_('Choose a valid birthday in the past.')) from None
        if values.get('terms') is not True or values.get('policy_version') != website.spx_mobile_policy_version:
            raise UserError(_('Read and accept the current terms and privacy policy.'))
        for field in ['marketing_email', 'marketing_sms']:
            if not isinstance(values.get(field, False), bool):
                raise UserError(_('Choose a valid marketing preference.'))
        city = values.get('city', '')
        if not isinstance(city, str) or len(city) > 100:
            raise UserError(_('Enter a city or town with fewer than 100 characters.'))
        self._lock_email(email)
        receipt = secrets.token_urlsafe(32)
        if self._users(email):
            # Do not alter any existing password, contact, user or card on public signup.
            self._queue_mail(website, email, 'Your Jenny’s account', 'Welcome back.',
                'An account already uses this email address. Sign in with your existing password, or use Forgot password in the app.', None)
            return receipt
        record = self.sudo().create({
            'website_id': website.id, 'email': email, 'kind': 'signup',
            'first_name': first.strip(), 'last_name': last.strip(), 'phone': '+1868'+phone.replace(' ', ''),
            'birthday': dob, 'city': city.strip(), 'marketing_email': values.get('marketing_email', False),
            'marketing_sms': values.get('marketing_sms', False), 'policy_version': website.spx_mobile_policy_version,
            'terms_at': fields.Datetime.now(), 'password_hash': self.env['res.users']._crypt_context().hash(pw),
            'receipt_hash': digest(receipt), 'expires_at': fields.Datetime.now()+timedelta(hours=24),
        })
        record._send_link()
        return receipt

    @api.model
    def _queue_mail(self, website, email, subject, title, text, link, registration=None):
        origin = (website.spx_mobile_account_origin or '').rstrip('/')
        body = Markup('''<div style="background:#f7f8fa;padding:32px;font-family:Arial,sans-serif;color:#172840">
          <div style="max-width:520px;margin:auto;background:#fff;padding:32px;border-radius:20px">
          <img src="%s/spx_loyalty_mobile/static/description/icon.png" width="64" height="64" alt="Jenny’s"/>
          <p style="color:#244e9d;letter-spacing:2px;font-size:12px">JENNY’S ON THE BOULEVARD</p>
          <h1 style="font-size:30px">%s</h1><p style="line-height:1.8">%s</p>%s
          <p style="font-size:12px;color:#697386;line-height:1.8">If you didn’t request this email, you can ignore it.</p>
          <p style="font-size:11px;color:#697386">Good food. Great company. Since 1987.</p></div></div>''') % (
            escape(origin), escape(title), escape(text),
            (Markup('<p style="margin:30px 0"><a style="display:inline-block;background:#244e9d;color:white;padding:16px 24px;border-radius:12px;text-decoration:none" href="%s">%s</a></p>') % (escape(link), 'Verify my email' if 'verify' in link else 'Reset my password')) if link else Markup(''))
        values = {
            'subject': subject, 'body_html': body, 'email_from': f'Jenny’s <{website.spx_mobile_mail_from}>',
            'email_to': email, 'auto_delete': True,
        }
        if registration is not None:
            registration.ensure_one()
            values.update({'model': self._name, 'res_id': registration.id})
        # Native system delivery owns the message, not the anonymous visitor.
        # send_after_commit opens a fresh superuser cursor only after the
        # registration/token are committed. Rollbacks never send a dead link.
        mail = self.env['mail.mail'].with_user(SUPERUSER_ID).create(values)
        mail.send_after_commit()
        return mail

    def _send_link(self):
        self.ensure_one()
        token = secrets.token_urlsafe(32)
        hours = 24 if self.kind == 'signup' else 1
        self.write({'token_hash': digest(token), 'sent_at': fields.Datetime.now(),
                    'expires_at': fields.Datetime.now()+timedelta(hours=hours)})
        path = 'verify' if self.kind == 'signup' else 'reset'
        origin = self.website_id.spx_mobile_account_origin.rstrip('/')
        link = f'{origin}/spx/mobile/account/{path}?token={token}'
        if self.kind == 'signup':
            self.mail_id = self._queue_mail(self.website_id, self.email, 'Verify your Jenny’s account',
                'A little welcome. Just for you.', 'Confirm your email to activate your account and digital loyalty card. This link expires in 24 hours.', link, registration=self)
        else:
            self.mail_id = self._queue_mail(self.website_id, self.email, 'Reset your Jenny’s password',
                'A fresh start.', 'Choose a new password for your Jenny’s account. This link expires in one hour.', link, registration=self)

    @api.model
    def _resend(self, website, receipt):
        if not isinstance(receipt, str) or not 30 <= len(receipt) <= 100:
            return
        record = self.sudo().search([('website_id', '=', website.id), ('receipt_hash', '=', digest(receipt)),
                                    ('kind', '=', 'signup'), ('state', '=', 'pending')], limit=1)
        if record and record.expires_at > fields.Datetime.now():
            record._lock_email(record.email)
            if not record.sent_at or record.sent_at < fields.Datetime.now()-timedelta(seconds=60):
                record._send_link()

    @api.model
    def _forgot(self, website, email):
        website._mobile_signup_config()
        email = email_value(email)
        self._lock_email(email)
        users = self._users(email)
        if len(users) != 1 or not users.active or not users.share or not users.has_group('base.group_portal'):
            return
        # Only recover an account whose actual email matches the verified destination.
        if email_value(users.email or '') != email:
            return
        self.sudo().search([('user_id', '=', users.id), ('kind', '=', 'reset'), ('state', '=', 'pending')]).write({
            'state': 'expired', 'token_hash': False})
        record = self.sudo().create({'website_id': website.id, 'email': email, 'kind': 'reset',
            'user_id': users.id, 'partner_id': users.partner_id.id,
            'expires_at': fields.Datetime.now()+timedelta(hours=1)})
        record._send_link()

    @api.model
    def _token(self, website, token, kind):
        if not isinstance(token, str) or not 30 <= len(token) <= 100:
            raise UserError(_('This link is invalid or expired. Request a new email in the app.'))
        record = self.sudo().search([('website_id', '=', website.id), ('token_hash', '=', digest(token)),
                                    ('kind', '=', kind)], limit=1)
        # A consumed signup link may show its success screen again, but never
        # authenticates a browser/app or changes an existing password/card.
        completed_signup = record and kind == 'signup' and record.state == 'done' and record.user_id
        if not completed_signup and (not record or record.state != 'pending' or record.expires_at <= fields.Datetime.now()):
            raise UserError(_('This link is invalid or expired. Request a new email in the app.'))
        return record

    def _complete(self, token, password=None):
        self.ensure_one()
        self._lock_email(self.email)
        self.env.cr.execute('SELECT id FROM spx_mobile_registration WHERE id=%s FOR UPDATE', (self.id,))
        self.invalidate_recordset()
        # Recheck after locking: resend may have rotated the link after lookup.
        if (not isinstance(token, str) or not 30 <= len(token) <= 100
                or not secrets.compare_digest(self.token_hash or '', digest(token))):
            raise UserError(_('This link is invalid or expired. Request a new email in the app.'))
        if self.kind == 'signup' and self.state == 'done' and self.user_id:
            return self.user_id
        if self.state != 'pending' or self.expires_at <= fields.Datetime.now():
            raise UserError(_('This link has already been used or has expired.'))
        website = self.website_id
        website._mobile_signup_config()
        if self.kind == 'reset':
            password_value(password)
            user = self.user_id
            if not user.active or not user.share or not user.has_group('base.group_portal') or email_value(user.email or '') != self.email:
                raise UserError(_('This account is unavailable. Please contact Jenny’s.'))
            user.with_context(no_reset_password=True).write({'password': password, 'spx_mobile_verified_email': self.email})
            self.sudo().search([('user_id', '=', user.id), ('kind', '=', 'signup')]).write({
                'handoff_hash': False, 'handoff_expires_at': False, 'receipt_hash': False})
        else:
            # The email link verifies ownership. Install only the password hash
            # captured at signup; the verification request supplies no password.
            scheme = self.env['res.users']._crypt_context().identify(self.password_hash or '')
            if not scheme or scheme == 'plaintext':
                raise UserError(_('This registration is incomplete. Please sign up again in the app.'))
            if self._users(self.email):
                raise UserError(_('An account already uses this email. Sign in or use Forgot password.'))
            partners = self.env['res.partner'].sudo().with_context(active_test=False).search([
                '|', ('email', '=ilike', escape_psql(self.email)), ('email_normalized', '=ilike', escape_psql(self.email))])
            if len(partners) > 1 or (partners and (not partners.active or partners.is_company or partners.parent_id
                    or partners.user_ids or (partners.company_id and partners.company_id != website.company_id))):
                raise UserError(_('Please contact Jenny’s to link your existing customer record.'))
            partner = partners or self.env['res.partner'].sudo().create({
                'name': f'{self.first_name} {self.last_name}', 'email': self.email, 'phone': self.phone,
                'city': self.city, 'company_id': website.company_id.id, 'is_company': False,
            })
            # Explicit portal-only groups; never trust client-supplied roles, partners or program IDs.
            user = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
                'name': partner.name, 'login': self.email, 'email': self.email, 'partner_id': partner.id,
                'password': secrets.token_urlsafe(48), 'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
                'company_id': website.company_id.id, 'company_ids': [Command.set([website.company_id.id])],
                'spx_mobile_verified_email': self.email,
            })
            user._set_encrypted_password(user.id, self.password_hash)
            partner.write({'spx_mobile_first_name': self.first_name, 'spx_mobile_last_name': self.last_name,
                'spx_mobile_birthday': self.birthday, 'spx_mobile_sms': self.marketing_sms,
                'spx_mobile_email': self.marketing_email, 'spx_mobile_verified_at': fields.Datetime.now(),
                'spx_mobile_policy_version': self.policy_version, 'spx_mobile_terms_at': self.terms_at})
            cards = self.env['loyalty.card'].sudo().with_context(active_test=False).search([
                ('partner_id', '=', partner.id), ('program_id', '=', website.spx_mobile_signup_program_id.id)], order='id', limit=1)
            if cards and not cards.active:
                raise UserError(_('Please contact Jenny’s to reactivate your existing loyalty card.'))
            card = cards or self.env['loyalty.card'].sudo().create({
                'partner_id': partner.id, 'program_id': website.spx_mobile_signup_program_id.id, 'points': 0})
            self.write({'user_id': user.id, 'partner_id': partner.id, 'card_id': card.id})
            self.sudo().search([('email', '=', self.email), ('kind', '=', 'signup'), ('state', '=', 'pending'), ('id', '!=', self.id)]).write({
                'state': 'expired', 'token_hash': False, 'receipt_hash': False, 'password_hash': False})
        self.write({'state': 'done', 'verified_at': fields.Datetime.now(),
                    'token_hash': self.token_hash if self.kind == 'signup' else False,
                    'receipt_hash': self.receipt_hash if self.kind == 'signup' else False, 'password_hash': False})
        return user

    @api.autovacuum
    def _gc(self):
        self.sudo().search([('handoff_expires_at', '<', fields.Datetime.now())]).write({
            'handoff_hash': False, 'handoff_expires_at': False})
        self.sudo().search([('state', '=', 'done'), ('verified_at', '<', fields.Datetime.now()-timedelta(days=1))]).write({
            'receipt_hash': False, 'handoff_hash': False, 'handoff_expires_at': False})
        self.sudo().search([('state', '=', 'pending'), ('expires_at', '<', fields.Datetime.now())]).write({
            'state': 'expired', 'password_hash': False, 'token_hash': False, 'receipt_hash': False})
        self.sudo().search([('state', '=', 'expired'), ('create_date', '<', fields.Datetime.now()-timedelta(days=30))]).unlink()
