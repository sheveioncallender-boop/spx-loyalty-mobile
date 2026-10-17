"""Passive customer app fields and tables; no business overrides or jobs."""
from uuid import uuid4
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    spx_mobile_signup_enabled = fields.Boolean('Enable verified signup', groups='base.group_system', prefetch=False)

    spx_mobile_signup_program_id = fields.Many2one('loyalty.program', string='New member loyalty program', groups='base.group_system', prefetch=False)

    spx_mobile_mail_from = fields.Char('Account email sender', default='no-reply@spxcorp.site', groups='base.group_system', prefetch=False)

    spx_mobile_account_origin = fields.Char('Account link origin', groups='base.group_system', prefetch=False, help='HTTPS origin only, for example https://jennys.spxcorp.site. Verification and recovery pages are served here.')

    spx_mobile_terms = fields.Text('Account and rewards terms', groups='base.group_system', prefetch=False)

    spx_mobile_privacy = fields.Text('Privacy policy', groups='base.group_system', prefetch=False)

    spx_mobile_policy_version = fields.Char('Policy version', default='1', groups='base.group_system', prefetch=False)


class Users(models.Model):
    _inherit = 'res.users'

    spx_mobile_verified_email = fields.Char('Verified app email', readonly=True, copy=False, groups='base.group_system', prefetch=False)

    spx_mobile_legacy_access = fields.Boolean('Existing member access', readonly=True, copy=False, groups='base.group_system', prefetch=False,
        help='Preserves access for portal accounts that already existed when verified signup was installed.')


class Partner(models.Model):
    _inherit = 'res.partner'

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
