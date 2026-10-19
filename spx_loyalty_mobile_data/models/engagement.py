"""Passive customer app fields and tables; no business overrides or jobs."""
from uuid import uuid4
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    spx_birthday_enabled = fields.Boolean('Enable birthday credit', groups='base.group_system', prefetch=False)

    spx_birthday_audience = fields.Selection([
        ('members', 'Verified app members'),
        ('customers', 'All customer contacts with a birthday'),
    ], default='members', required=True, groups='base.group_system', prefetch=False)

    spx_birthday_field_id = fields.Many2one(
        'ir.model.fields', string='Existing customer birthday field',
        domain="[('model', '=', 'res.partner'), ('ttype', '=', 'date'), ('store', '=', True)]",
        groups='base.group_system', prefetch=False, ondelete='set null',
        help='Optional existing contact date field. Used when filled; otherwise the app signup birthday is used. No dates are copied or overwritten.')

    spx_birthday_program_id = fields.Many2one('loyalty.program', string='Birthday credit program', groups='base.group_system', prefetch=False,
        domain="[('program_type', '=', 'gift_card')]",
        help='Use a separate native gift-card program for promotional credit, not your purchased gift-card program.')

    spx_birthday_amount = fields.Monetary('Birthday credit amount', currency_field='currency_id', groups='base.group_system', prefetch=False)

    spx_birthday_days = fields.Integer('Birthday validity (days)', default=21, groups='base.group_system', prefetch=False)

    spx_birthday_message = fields.Text('Birthday greeting', default='Happy birthday! Enjoy a little treat from Jenny’s. Your birthday credit is ready in Rewards.', groups='base.group_system', prefetch=False)

    spx_member_timezone = fields.Char('Member timezone', default='America/Port_of_Spain', groups='base.group_system', prefetch=False)

    spx_gift_program_ids = fields.Many2many('loyalty.program', 'spx_mobile_gift_program_rel', 'website_id', 'program_id',
        string='Purchased gift card programs', groups='base.group_system', domain="[('program_type', '=', 'gift_card')]")

    spx_gift_product_ids = fields.Many2many('product.template', 'spx_mobile_gift_product_rel', 'website_id', 'product_id',
        string='Gift cards available to buy', groups='base.group_system',
        help='Existing published native gift-card products. Their price and value are controlled by the native program and pricelist.')


class Partner(models.Model):
    _inherit = 'res.partner'

    spx_member_announcements = fields.Boolean('App event announcements', default=True, prefetch=False)


class BirthdayAward(models.Model):
    _name = 'spx.mobile.birthday.award'

    _description = 'Annual birthday credit'

    _order = 'issued_on desc, id desc'

    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', readonly=True, index=True)

    website_id = fields.Many2one('website', required=True, ondelete='restrict', readonly=True)

    company_id = fields.Many2one('res.company', required=True, ondelete='restrict', readonly=True)

    year = fields.Integer(required=True, readonly=True)

    issued_on = fields.Date(required=True, readonly=True)

    card_id = fields.Many2one('loyalty.card', required=True, ondelete='restrict', readonly=True)

    currency_id = fields.Many2one(related='card_id.currency_id')

    amount = fields.Monetary(readonly=True)

    expires = fields.Date(related='card_id.expiration_date')

    balance = fields.Float(related='card_id.points')

    _annual_unique = models.Constraint('UNIQUE(company_id, partner_id, year)', 'This member already received birthday credit this year.')


class Announcement(models.Model):
    _name = 'spx.mobile.announcement'

    _description = 'Jenny’s event announcement'

    _order = 'id desc'

    name = fields.Char('Title', required=True)

    body = fields.Text('Message', required=True)

    website_id = fields.Many2one('website', required=True, default=lambda self: self.env['website'].search([], limit=1))

    company_id = fields.Many2one(related='website_id.company_id', store=True)

    audience = fields.Selection([('all', 'All members'), ('selected', 'Selected members')], default='all', required=True)

    partner_ids = fields.Many2many('res.partner', string='Members')

    scheduled_at = fields.Datetime('Publish at')

    state = fields.Selection([('draft', 'Draft'), ('scheduled', 'Scheduled'), ('published', 'Published'), ('cancelled', 'Cancelled')], default='draft', required=True, readonly=True, copy=False)

    published_at = fields.Datetime(readonly=True, copy=False)

    message_ids = fields.One2many('spx.mobile.message', 'announcement_id', readonly=True)

    delivery_note = fields.Char(default='App inbox only. Device push will be enabled after Firebase setup.', readonly=True)


class Message(models.Model):
    _inherit = 'spx.mobile.message'

    announcement_id = fields.Many2one('spx.mobile.announcement', readonly=True, ondelete='restrict', index=True)

    _announcement_member_unique = models.Constraint('UNIQUE(announcement_id, partner_id)', 'This announcement has already been delivered to this member.')
