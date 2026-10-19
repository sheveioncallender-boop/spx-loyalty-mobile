"""Gift delivery metadata only. No copied balance or custom payment processing."""


from markupsafe import Markup, escape
from odoo import _, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from .onboarding import email_value


class GiftDelivery(models.Model):
    _inherit = 'spx.mobile.gift.delivery'

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        # Delivery metadata is immutable to admins, but native email retries
        # must still be able to update the linked message after SMTP accepts it.
        if message_operation == 'write' and self.env.user.has_group('base.group_system'):
            return dict.fromkeys(self, 'read')
        return super()._mail_get_operation_for_mail_message_operation(message_operation)

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
