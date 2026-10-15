"""Passive customer app fields and tables; no business overrides or jobs."""
from uuid import uuid4
from odoo import fields, models


class GiftDelivery(models.Model):
    _name = 'spx.mobile.gift.delivery'

    _description = 'Customer gift card delivery'

    _order = 'id desc'

    _rec_name = 'recipient_email'

    website_id = fields.Many2one('website', required=True, ondelete='restrict', readonly=True)

    company_id = fields.Many2one(related='website_id.company_id', store=True)

    sender_id = fields.Many2one('res.partner', required=True, ondelete='restrict', readonly=True)

    recipient_id = fields.Many2one('res.partner', required=True, ondelete='restrict', readonly=True)

    recipient_email = fields.Char(required=True, readonly=True)

    card_id = fields.Many2one('loyalty.card', required=True, ondelete='restrict', readonly=True)

    message = fields.Text(readonly=True)

    request_key = fields.Char(required=True, readonly=True)

    mail_id = fields.Many2one('mail.mail', readonly=True, ondelete='set null')

    mail_state = fields.Selection(related='mail_id.state')

    _card_once = models.Constraint('UNIQUE(card_id)', 'This card has already been sent as a gift.')

    _request_once = models.Constraint('UNIQUE(sender_id, website_id, request_key)', 'This gift request was already processed.')
