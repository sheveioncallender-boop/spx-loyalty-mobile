from odoo import _, http, fields
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools import escape_psql

from .api import MobileAPI
from .validation import positive_id, mutation_id
from ..models.onboarding import email_value


class EngagementAPI(MobileAPI):
    def _gift_rate(self, w, partner):
        if not request.env['spx.mobile.account.rate'].sudo()._allow(w, 'gift:%s' % partner.id):
            raise UserError(_('Please wait before trying another gift card.'))

    def _gift_programs(self, w):
        return w.spx_gift_program_ids.filtered(lambda p: p.active and p.program_type == 'gift_card'
            and (not p.company_id or p.company_id == w.company_id) and (not p.website_id or p.website_id == w)
            and p != w.spx_birthday_program_id)

    def _issued_card(self, card):
        """Never disclose draft purchase codes. Native confirmed payments remain authoritative."""
        if card.order_id:
            order = card.order_id
            # Reuse the native paid check; an authorization is not captured payment.
            captured = (order._is_paid() and not order.transaction_ids.filtered(lambda t: t.state == 'authorized'))
            invoices = order.invoice_ids.filtered(lambda i: i.move_type == 'out_invoice' and i.state != 'cancel')
            invoiced_paid = (order.invoice_status == 'invoiced' and bool(invoices)
                and all(i.state == 'posted' and i.payment_state == 'paid' for i in invoices))
            return order.state == 'sale' and order.amount_total > 0 and (captured or invoiced_paid)
        if card.source_pos_order_id:
            return card.source_pos_order_id.state in ('paid', 'done', 'invoiced')
        # Cards issued directly by staff are supported, as they are in native POS.
        return True

    def _gift_cards(self, w, partner):
        return request.env['loyalty.card'].sudo().search([
            ('program_id', 'in', self._gift_programs(w).ids),
            '|', ('partner_id', '=', partner.id), '&', ('partner_id', '=', False), ('order_id.partner_id', '=', partner.id),
        ]).filtered(self._issued_card)

    def _card_data(self, c, today):
        expired = bool(c.expiration_date and c.expiration_date < today)
        return {'id': c.id, 'name': c.program_id.name, 'number': c.code if not expired and c.points > 0 else '',
            'balance': c.points, 'currency': c.currency_id.name,
            'expires': self._date(c.expiration_date), 'state': 'expired' if expired else 'empty' if c.points <= 0 else 'active'}

    @http.route('/spx/mobile/v1/wallet', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def wallet(self):
        w, partner = self._scope()
        today = w._spx_today()
        gifts = self._gift_cards(w, partner)
        already_sent = request.env['spx.mobile.gift.delivery'].sudo().search([('card_id', 'in', gifts.ids)]).card_id
        awards = request.env['spx.mobile.birthday.award'].sudo().search([
            ('website_id', '=', w.id), ('partner_id', '=', partner.id)], limit=10)
        birthday = [dict(self._card_data(a.card_id, today), kind='birthday') for a in awards if a.card_id.active and a.card_id.program_id.active and a.card_id.partner_id == partner]
        products = w.spx_gift_product_ids.filtered(lambda p: p.active and p.sale_ok and p.is_published
            and (not p.website_id or p.website_id == w) and (not p.company_id or p.company_id == w.company_id)
            and any(v in self._gift_programs(w).filtered('ecommerce_ok').trigger_product_ids for v in p.product_variant_ids))
        deliveries = request.env['spx.mobile.gift.delivery'].sudo().search([
            ('website_id', '=', w.id), ('sender_id', '=', partner.id)], limit=30)
        return {'gift_cards': [dict(self._card_data(c, today), kind='gift', can_send=c not in already_sent) for c in gifts], 'birthday_credits': birthday,
            'products': [{'id': p.id, 'name': p.name, 'path': p.website_url} for p in products],
            'sent_gifts': [{'id': d.id, 'email': d.recipient_email,
                'state': 'sent' if d.mail_id.state == 'sent' else 'failed' if d.mail_id.state in ('exception', 'cancel') else 'queued',
                'date': self._date(d.create_date)} for d in deliveries],
            'can_add': bool(self._gift_programs(w)), 'announcements': partner.sudo().spx_member_announcements}

    @http.route('/spx/mobile/v1/gifts/add', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def add_gift(self, code):
        w, partner = self._scope()
        self._gift_rate(w, partner)
        if not isinstance(code, str) or not 1 <= len(code.strip()) <= 128:
            raise UserError(_('Enter the full gift card code.'))
        c = request.env['loyalty.card'].sudo().search([('code', '=', code.strip()), ('program_id', 'in', self._gift_programs(w).ids)], limit=1)
        if c:
            request.env.cr.execute('SELECT id FROM loyalty_card WHERE id = %s FOR UPDATE', (c.id,))
            c.invalidate_recordset()
        if (not c or not c.active or c.points <= 0 or (c.expiration_date and c.expiration_date < w._spx_today())
                or (c.partner_id and c.partner_id != partner) or not self._issued_card(c)):
            raise UserError(_('This card cannot be added. Check the code or ask Jenny’s for help.'))
        # The full code is a bearer credential for an unassigned physical/digital card.
        if not c.partner_id:
            c.write({'partner_id': partner.id})
        return {'ok': True}

    @http.route('/spx/mobile/v1/gifts/send', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def send_gift(self, card_id, recipient_email, recipient_name, message='', key=None):
        w, partner = self._scope()
        self._gift_rate(w, partner)
        try:
            card_id, key = positive_id(card_id), mutation_id(key)
        except ValueError as error:
            raise UserError(str(error)) from error
        email = email_value(recipient_email)
        if (not isinstance(recipient_name, str) or not 1 <= len(recipient_name.strip()) <= 100
                or not isinstance(message, str) or len(message) > 500):
            raise UserError(_('Enter a recipient name and a message of up to 500 characters.'))
        if email == email_value(partner.email):
            raise UserError(_('Choose someone else to send this gift to.'))
        model = request.env['spx.mobile.gift.delivery'].sudo()
        request.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (739402, partner.id))
        existing = model.search([('sender_id', '=', partner.id), ('website_id', '=', w.id), ('request_key', '=', key)], limit=1)
        if existing:
            if existing.card_id.id != card_id or existing.recipient_email != email:
                raise UserError(_('Start a new gift request.'))
            return {'ok': True}
        card = self._gift_cards(w, partner).filtered(lambda c: c.id == card_id)
        if card:
            request.env.cr.execute('SELECT id FROM loyalty_card WHERE id = %s FOR UPDATE', (card.id,))
            card.invalidate_recordset()
        if (not card or card not in self._gift_cards(w, partner) or card.points <= 0
                or (card.expiration_date and card.expiration_date < w._spx_today())
                or model.search_count([('card_id', '=', card_id)])):
            raise UserError(_('This gift card cannot be sent. Refresh your cards or contact Jenny’s.'))
        # Serialize email matching with onboarding's own unique-email boundary; a
        # gift recipient is a contact only, never an automatically created user.
        request.env['spx.mobile.registration'].sudo()._lock_email(email)
        matches = request.env['res.partner'].sudo().with_context(active_test=False).search([
            '|', ('email_normalized', '=', email), ('email', '=ilike', escape_psql(email))])
        if len(matches) > 1 or (matches and (matches.is_company or matches.parent_id or not matches.active or any(not u.share for u in matches.user_ids))):
            raise UserError(_('Please ask Jenny’s to help send this gift to that recipient.'))
        recipient = matches or request.env['res.partner'].sudo().create({'name': recipient_name.strip(), 'email': email,
            'company_type': 'person'})
        delivery = model.create({'website_id': w.id, 'sender_id': partner.id, 'recipient_id': recipient.id,
            'recipient_email': email, 'card_id': card.id, 'message': message.strip(), 'request_key': key})
        card.write({'partner_id': recipient.id})
        delivery._queue_delivery()
        return {'ok': True}

    @http.route('/spx/mobile/v1/announcements/preference', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def announcement_preference(self, enabled):
        w, partner = self._scope()
        if not isinstance(enabled, bool):
            raise UserError(_('Choose a valid preference.'))
        partner.sudo().spx_member_announcements = enabled
        return {'ok': True}
