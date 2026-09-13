"""Versioned customer facade. No client-supplied balances, prices or partner IDs.

Use Odoo's existing /web/session/authenticate before these JSON-RPC endpoints.
Every sudo read below follows an explicit website, company and customer scope.
"""
from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale

from .validation import positive_id, quantity, mutation_id


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
            'capabilities': {'cart': True, 'inbox': True, 'push': False, 'checkout': 'odoo'},
        }

    def _product_domain(self, website):
        return website.sale_product_domain() + [('is_published', '=', True)]

    def _simple_product(self, template):
        return (template.product_variant_count == 1 and template.type != 'combo'
                and not template.attribute_line_ids)

    def _require_shop_access(self, website):
        if not website.has_ecommerce_access():
            raise AccessError(_('Online ordering is not available for this account.'))

    @http.route('/spx/mobile/v1/catalog', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def catalog(self, offset=0):
        website, partner = self._scope()
        self._require_shop_access(website)
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 10000:
            raise UserError(_('Invalid catalog page.'))
        templates = request.env['product.template'].search(
            self._product_domain(website), order='website_sequence, id', limit=41, offset=offset)
        items = []
        for template in templates[:40]:
            info = template._get_combination_info()
            product = request.env['product.product'].browse(info.get('product_id'))
            items.append({
                'id': template.id, 'product_id': info.get('product_id') or None,
                'name': template.name, 'description': html2plaintext(template.description_ecommerce or template.description_sale or ''),
                'price': info['price'], 'currency': website.currency_id.name,
                'category': template.public_categ_ids[:1].name or _('Menu'),
                'image': self._product_image(template, 512),
                'url': template.website_url,
                'direct_add': bool(product and self._simple_product(template)
                                   and product._is_add_to_cart_allowed()
                                   and info.get('is_combination_possible')
                                   and not info.get('prevent_zero_price_sale')),
            })
        return {'items': items, 'next_offset': offset + 40 if len(templates) > 40 else None}

    def _cart(self, website, partner, create=False):
        self._require_shop_access(website)
        order = request.cart
        if not order and create:
            order = website._create_cart()
        # Check new carts too: installed model extensions must preserve scope.
        if order and (order.partner_id != partner or order.website_id != website
                      or order.company_id != website.company_id or order.state != 'draft'):
            raise AccessError(_('This cart is not available for this account.'))
        return order

    def _cart_data(self, order, website, partner):
        if not order:
            return {'lines': [], 'total': 0, 'tax': 0, 'subtotal': 0,
                    'currency': website.currency_id.name, 'rewards': []}
        own_cards = self._cards(website, partner)
        eligible = order._get_claimable_and_showable_rewards()
        rewards = []
        for card, available in eligible.items():
            if card not in own_cards:
                continue
            for reward in available:
                rewards.append({**self._reward(reward), 'card_id': card.id,
                                'products': [{'id': p.id, 'name': p.display_name}
                                             for p in reward.reward_product_ids]})
        return {
            'id': order.id, 'name': order.name, 'currency': order.currency_id.name,
            'total': order.amount_total, 'tax': order.amount_tax, 'subtotal': order.amount_untaxed,
            'lines': [{'id': line.id, 'name': line.name, 'qty': line.product_uom_qty,
                       'total': line.price_total, 'reward': bool(line.reward_id),
                       'editable': not bool(line.reward_id or line.is_delivery),
                       'image': self._product_image(line.product_id, 128)}
                      for line in order.order_line if not line.display_type],
            'rewards': rewards,
        }

    @http.route('/spx/mobile/v1/cart', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def cart(self):
        website, partner = self._scope()
        return self._cart_data(self._cart(website, partner), website, partner)

    @http.route('/spx/mobile/v1/cart/add', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def cart_add(self, product_id, qty, request_id):
        website, partner = self._scope()
        try:
            product_id, qty, request_id = positive_id(product_id), quantity(qty), mutation_id(request_id)
        except ValueError as error:
            raise UserError(str(error)) from error
        product = request.env['product.product'].search(
            [('id', '=', product_id)] + self._product_domain(website), limit=1)
        if not product or not self._simple_product(product.product_tmpl_id):
            raise UserError(_('Please select the options for this item on our online menu.'))
        # The native /shop/cart/add controller makes this check before _cart_add.
        # Calling the model mutation alone would skip website/custom product vetoes.
        if not product._is_add_to_cart_allowed():
            raise UserError(_('This item is not available for online ordering.'))
        order = self._cart(website, partner, create=True)
        operations = request.env['spx.mobile.operation'].sudo()
        previous = operations.search([
            ('partner_id', '=', partner.id), ('website_id', '=', website.id), ('key', '=', request_id),
        ], limit=1)
        if previous and previous.order_id != order:
            raise UserError(_('This request belongs to an earlier cart. Refresh your order.'))
        if not previous:
            # The unique database constraint rejects concurrent duplicate requests.
            # The marker and the native cart mutation commit or roll back together.
            operations.create({'key': request_id, 'partner_id': partner.id,
                               'website_id': website.id, 'order_id': order.id})
            result = order._cart_add(product_id, quantity=qty)
        else:
            result = {}
        return {**self._cart_data(order, website, partner), 'warning': result.get('warning') or None}

    @http.route('/spx/mobile/v1/cart/update', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def cart_update(self, line_id, qty):
        website, partner = self._scope()
        try:
            line_id, qty = positive_id(line_id), quantity(qty, allow_zero=True)
        except ValueError as error:
            raise UserError(str(error)) from error
        order = self._cart(website, partner)
        line = order.order_line.filtered(lambda line: line.id == line_id) if order else False
        if not line or line.reward_id or line.is_delivery:
            raise AccessError(_('This cart item cannot be changed.'))
        result = order._cart_update_line_quantity(line_id, quantity=qty)
        return {**self._cart_data(order, website, partner), 'warning': result.get('warning') or None}

    @http.route('/spx/mobile/v1/cart/reward', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def cart_reward(self, reward_id, card_id, product_id=None):
        website, partner = self._scope()
        try:
            reward_id, card_id = positive_id(reward_id), positive_id(card_id)
            if product_id is not None:
                product_id = positive_id(product_id)
        except ValueError as error:
            raise UserError(str(error)) from error
        order = self._cart(website, partner)
        if not order:
            raise UserError(_('Add an item to your order first.'))
        own_cards = self._cards(website, partner)
        for card, rewards in order._get_claimable_and_showable_rewards().items():
            reward = rewards.filtered(lambda r: r.id == reward_id)
            if card.id != card_id or card not in own_cards or not reward:
                continue
            if reward.multi_product and product_id not in reward.reward_product_ids.ids:
                raise UserError(_('Choose a product included in this reward.'))
            if not reward.multi_product and product_id is not None:
                raise UserError(_('This reward does not accept a product selection.'))
            request.update_context(product_id=product_id)
            if not WebsiteSale()._apply_reward(order, reward, card):
                raise UserError(request.session.pop('error_promo_code', None) or _('This reward is unavailable.'))
            return self._cart_data(order, website, partner)
        raise UserError(_('This reward is not available for your current order.'))

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
