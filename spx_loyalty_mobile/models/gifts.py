"""Gift delivery metadata only. No copied balance or custom payment processing."""
from markupsafe import Markup, escape

from odoo import _, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from .onboarding import email_value


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

    def _queue_delivery(self):
        self.ensure_one()
        if self.mail_id:
            return
        sender = self.website_id.spx_mobile_mail_from
        email_value(sender)
        body = Markup('<h2>A little Jenny’s, just for you.</h2><p>%s sent you a Jenny’s gift card.</p><p>%s</p><p>Gift card: <strong>%s</strong></p><p>Present this code at Jenny’s or use it at online checkout. Sign up in the app with this email to see your card there too.</p>') % (
            escape(self.sender_id.name), escape(self.message or ''), escape(self.card_id.code))
        self.mail_id = self.env['mail.mail'].with_user(SUPERUSER_ID).create({
            'subject': 'A Jenny’s gift card for you', 'body_html': body,
            'email_from': sender, 'email_to': self.recipient_email,
            'author_id': self.website_id.company_id.partner_id.id, 'auto_delete': False,
            'model': self._name, 'res_id': self.id,
        })
