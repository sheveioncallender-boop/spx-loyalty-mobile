"""Versioned customer facade. No client-supplied balances, prices or partner IDs.

Use Odoo's existing /web/session/authenticate before these JSON-RPC endpoints.
Every sudo read below follows an explicit website, company and customer scope.
"""
from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from .validation import positive_id


class MobileAPI(http.Controller):
    def _scope(self):
        user = request.env.user
        if not user.has_group('base.group_portal') or not user.share:
            raise AccessError(_('Use an individual customer portal account to sign in.'))
        website = request.website.sudo()
        if not website.spx_mobile_enabled:
            raise AccessError(_('The customer app has not been enabled for this website.'))
        return website, user.partner_id

    def _programs(self, website):
        return website.spx_mobile_program_ids.filtered(lambda p:
            p.active and p.program_type == 'loyalty'
            and (not p.company_id or p.company_id == website.company_id)
            and (not p.website_id or p.website_id == website))

    def _cards(self, website, partner):
        return request.env['loyalty.card'].sudo().search([
            ('partner_id', '=', partner.id),
            ('program_id', 'in', self._programs(website).ids),
        ], order='id desc', limit=100)

    def _date(self, value):
        return value.isoformat() if value else None

    def _product_image(self, record, size):
        # A stable revision changes only when the native product is updated.
        # This lets mobile image caches reuse unchanged pictures and fetch edits.
        dates = [record.write_date]
        if record._name == 'product.product':
            dates.append(record.product_tmpl_id.write_date)
        revision = max((date for date in dates if date), default=None)
        token = revision.strftime('%Y%m%d%H%M%S%f') if revision else '0'
        return '/web/image/%s/%s/image_%s?unique=%s' % (record._name, record.id, size, token)

    def _reward(self, reward):
        return {'id': reward.id, 'name': reward.description or reward.program_id.name,
                'program_id': reward.program_id.id, 'points': reward.required_points,
                'type': reward.reward_type, 'needs_selection': reward.multi_product}

    @http.route('/spx/mobile/v1/bootstrap', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def bootstrap(self):
        website, partner = self._scope()
        cards = self._cards(website, partner)
        history = request.env['loyalty.history'].sudo().search([
            ('card_id', 'in', cards.ids)], limit=40, order='id desc')
        messages = request.env['spx.mobile.message'].sudo().search([
            ('partner_id', '=', partner.id), ('website_id', '=', website.id)], limit=40)
        return {
            'api_version': 1,
            'brand': website.spx_mobile_brand or website.name,
            'customer': {'name': partner.name, 'email': partner.email or '',
                         'promotional_email': partner.spx_mobile_email},
            'currency': website.currency_id.name,
            'cards': [{'id': c.id, 'name': c.program_id.name, 'number': c.code,
                       'program_id': c.program_id.id, 'points': c.points,
                       'point_name': c.program_id.portal_point_name or _('Points'),
                       'expires': self._date(c.expiration_date),
                       'since': self._date(c.create_date)} for c in cards],
            'rewards': [self._reward(r) for r in self._programs(website).reward_ids],
            'activity': [{'id': h.id, 'card_id': h.card_id.id, 'name': h.description,
                          'issued': h.issued, 'used': h.used, 'date': self._date(h.create_date)} for h in history],
            'messages': [{'id': m.id, 'name': m.name, 'body': m.body,
                          'read': bool(m.read_at), 'date': self._date(m.create_date)} for m in messages],
            'capabilities': {'cart': bool(website.spx_mobile_pos_config_id), 'inbox': True,
                             'push': False, 'checkout': 'dine_in', 'ordering_api': 2},
        }

    def _simple_product(self, template):
        return (template.product_variant_count == 1 and template.type != 'combo'
                and not template.attribute_line_ids)

    @http.route([
        '/spx/mobile/v1/catalog', '/spx/mobile/v1/cart', '/spx/mobile/v1/cart/add',
        '/spx/mobile/v1/cart/update', '/spx/mobile/v1/cart/reward',
    ], type='jsonrpc', auth='user', website=True, methods=['POST'])
    def legacy_cart(self, **_params):
        self._scope()
        raise UserError(_('Please update Jenny’s app to place dine-in orders.'))

    @http.route('/spx/mobile/v1/orders', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def orders(self):
        website, partner = self._scope()
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id), ('website_id', '=', website.id),
            ('company_id', '=', website.company_id.id), ('state', 'in', ['sale', 'cancel']),
        ], order='date_order desc, id desc', limit=40)
        return [{'name': o.name, 'date': self._date(o.date_order), 'total': o.amount_total,
                 'currency': o.currency_id.name, 'state': o.state} for o in orders]

    @http.route('/spx/mobile/v1/preferences', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def preferences(self, promotional_email):
        website, partner = self._scope()
        if not isinstance(promotional_email, bool):
            raise UserError(_('Choose a valid email preference.'))
        partner.sudo().write({'spx_mobile_email': promotional_email})
        return {'promotional_email': partner.spx_mobile_email}

    @http.route('/spx/mobile/v1/messages/read', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def message_read(self, message_id):
        website, partner = self._scope()
        try:
            message_id = positive_id(message_id)
        except ValueError as error:
            raise UserError(str(error)) from error
        message = request.env['spx.mobile.message'].sudo().search([
            ('id', '=', message_id), ('partner_id', '=', partner.id), ('website_id', '=', website.id)], limit=1)
        if not message:
            raise AccessError(_('This message is unavailable.'))
        message.write({'read_at': fields.Datetime.now()})
        return {'ok': True}
