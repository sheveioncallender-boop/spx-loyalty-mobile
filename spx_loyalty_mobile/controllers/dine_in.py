"""Authenticated baskets -> new, unpaid native POS orders.

No POS assets, model overrides, table assignment, kitchen dispatch, payments or
loyalty writes. Staff own those actions in Odoo's unmodified POS interface.
"""
import hashlib
import json
from uuid import uuid4

from psycopg2.errors import SerializationFailure, UniqueViolation

from odoo import _, Command, fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import html2plaintext

from .api import MobileAPI
from .validation import mutation_id, positive_id, quantity


class DineInAPI(MobileAPI):
    def _config(self, website, required=False):
        config = website.spx_mobile_pos_config_id.with_company(website.company_id)
        if config and (not config.active or not config.module_pos_restaurant
                       or config.company_id != website.company_id):
            raise UserError(_('Ordering is temporarily unavailable. Please speak to Jenny’s.'))
        if required and not config:
            raise UserError(_('Dine-in ordering will be available soon. Please order with our team.'))
        return config

    def _owner_domain(self, website, partner):
        return [('partner_id', '=', partner.id), ('website_id', '=', website.id)]

    def _basket(self, website, partner, lock=False):
        model = request.env['spx.mobile.basket'].sudo()
        basket = model.search(self._owner_domain(website, partner), limit=1)
        created = False
        if lock and not basket:
            try:
                with request.env.cr.savepoint():
                    basket = model.create({'partner_id': partner.id, 'website_id': website.id})
                    created = True
            except UniqueViolation as error:
                # Odoo retries the whole transaction with a fresh snapshot.
                # No order or external action can commit in this failed attempt.
                raise SerializationFailure('Concurrent basket creation; retry transaction') from error
        if lock:
            request.env.cr.execute('SELECT id FROM spx_mobile_basket WHERE id = %s FOR UPDATE', [basket.id])
            basket.invalidate_recordset()
        return basket, created

    def _check_key(self, basket, key, created=False):
        if created and key is None:
            return
        if not isinstance(key, str) or key != basket.token:
            raise UserError(_('Your basket changed. Refresh and review it before continuing.'))

    def _menu_domain(self, website, config):
        domain = request.env['product.template'].sudo()._load_pos_data_domain({}, config) + [
            ('active', '=', True),
            ('is_published', '=', True), ('website_id', 'in', [False, website.id]),
            ('company_id', 'in', [False, website.company_id.id]),
        ]
        return domain

    def _products(self, website, config):
        return request.env['product.product'].sudo().with_company(website.company_id).with_context(website_id=website.id)

    def _can_add(self, product):
        return (self._simple_product(product.product_tmpl_id)
                and not product.to_weight and product.tracking == 'none')

    def _order_context(self, config, partner):
        """Use the same configured customer/preset priorities as native POS."""
        partner = partner.sudo().with_company(config.company_id)
        preset = config.default_preset_id if config.use_presets else request.env['pos.preset']
        if preset and (preset.is_return or preset.identification == 'address' or preset.use_timing):
            raise UserError(_('Dine-in ordering is temporarily unavailable. Please order with our team.'))
        pricelist = partner.property_product_pricelist
        if not config.use_pricelist or pricelist not in config.available_pricelist_ids:
            pricelist = config.pricelist_id
        fiscal_position = partner.fiscal_position_id
        if fiscal_position not in config.fiscal_position_ids:
            fiscal_position = config.default_fiscal_position_id
        if preset:
            pricelist = preset.pricelist_id or pricelist
            fiscal_position = preset.fiscal_position_id or fiscal_position
        if ((pricelist and pricelist.company_id and pricelist.company_id != config.company_id)
                or (fiscal_position and fiscal_position.company_id != config.company_id)):
            raise AccessError(_('Ordering is unavailable for this account. Please speak to Jenny’s.'))
        return {
            'config_id': config.id, 'session_id': config.current_session_id.id,
            'company_id': config.company_id.id, 'partner_id': partner.id,
            'pricelist_id': pricelist.id, 'fiscal_position_id': fiscal_position.id,
            'preset_id': preset.id, 'state': 'draft', 'amount_paid': 0,
            'amount_return': 0, 'amount_tax': 0, 'amount_total': 0,
            # Use the session operator, never a customer as the cashier.
            'user_id': config.current_session_id.user_id.id or False,
        }

    def _priced_order(self, config, partner, entries):
        """Quote on unsaved native records; native pricelists and tax routines.

        A read/quote creates no POS bill, payment, picking or loyalty entry.
        """
        values = self._order_context(config, partner)
        model = request.env['pos.order'].sudo().with_company(config.company_id)
        order = model.new(values)
        line_values = []
        for product, qty in entries:
            product = product.with_company(config.company_id)
            taxes = product.taxes_id._filter_taxes_by_company(config.company_id)
            mapped = order.fiscal_position_id.map_tax(taxes)
            if order.pricelist_id:
                price = order.pricelist_id._get_product_price(product, qty, currency=config.currency_id)
            else:
                price = product.currency_id._convert(
                    product.lst_price, config.currency_id, config.company_id, fields.Date.context_today(order))
            price = request.env['account.tax']._fix_tax_included_price_company(
                price, taxes, mapped, config.company_id)
            line_values.append({
                'product_id': product.id, 'qty': qty, 'price_unit': price, 'discount': 0,
                'tax_ids': [Command.set(taxes.ids)], 'full_product_name': product.display_name,
                'price_subtotal': 0, 'price_subtotal_incl': 0, 'price_type': 'original',
            })
        order.update({'lines': [Command.create(value) for value in line_values]})
        for line, value in zip(order.lines, line_values):
            amounts = line._compute_amount_line_all()
            line.update(amounts)
            value.update(amounts)
        order._compute_prices()
        values.update({'amount_tax': order.amount_tax, 'amount_total': order.amount_total,
                       'amount_difference': order.amount_difference})
        return order, values, line_values

    def _receipt(self, submission):
        # Snapshot only. Never dereference a bill now merged with another guest.
        return dict(submission.receipt or {})

    def _cart_data_v2(self, website, partner, basket=None):
        config = self._config(website)
        if basket is None:
            basket, _created = self._basket(website, partner)
        result = {'lines': [], 'total': 0, 'subtotal': 0, 'tax': 0, 'rewards': [],
                  'currency': config.currency_id.name if config else website.currency_id.name,
                  'basket_key': basket.token if basket else None, 'quote': None,
                  'can_submit': False, 'service': 'dine_in', 'warning': None}
        previous = request.env['spx.mobile.submission'].sudo().search(
            self._owner_domain(website, partner), limit=1)
        result['last_order'] = self._receipt(previous) if previous else None
        if not config:
            result['warning'] = _('Dine-in ordering will be available soon. Please order with our team.')
            return result, None, None
        selections = basket.items or {} if basket else {}
        products = self._products(website, config).search(
            self._menu_domain(website, config) + [('id', 'in', [int(key) for key in selections])])
        eligible = {p.id: p for p in products if self._can_add(p)}
        entries = [(eligible[int(key)], value['qty']) for key, value in selections.items() if int(key) in eligible]
        order, values, line_values = self._priced_order(config, partner, entries)
        prices = {line.product_id.id: line for line in order.lines}
        for key, value in selections.items():
            pid = int(key)
            line = prices.get(pid)
            result['lines'].append({
                'id': pid, 'name': eligible[pid].display_name if line else value['name'],
                'qty': value['qty'], 'total': line.price_subtotal_incl if line else 0,
                'editable': True, 'reward': False, 'available': bool(line),
                'image': self._product_image(eligible[pid], 128) if line else '',
            })
        unavailable = len(entries) != len(selections)
        result.update({'total': order.amount_total, 'tax': order.amount_tax,
                       'subtotal': order.amount_total - order.amount_tax})
        opened = config.current_session_id.state == 'opened'
        result['can_submit'] = bool(entries) and not unavailable and opened and order.amount_total >= 0
        if unavailable:
            result['warning'] = _('Some items are no longer available. Remove them to continue.')
        elif not opened:
            result['warning'] = _('We’re not accepting app orders right now. Please speak to our team.')
        if basket:
            # Bound to owner, basket revision, destination, current session and
            # exact native prices/taxes. Recomputed again inside submission.
            digest = {'key': basket.token, 'website': website.id, 'values': values, 'lines': line_values}
            result['quote'] = hashlib.sha256(json.dumps(digest, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        return result, values, line_values

    @http.route('/spx/mobile/v2/dine-in/catalog', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_catalog(self, offset=0):
        website, partner = self._scope()
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 10000:
            raise UserError(_('Invalid menu page.'))
        config = self._config(website)
        if not config:
            return {'items': [], 'next_offset': None}
        products = self._products(website, config).search(
            self._menu_domain(website, config), order='pos_sequence, id', limit=41, offset=offset)
        items = []
        for product in products[:40]:
            if self._can_add(product):
                quote, _values, _lines = self._priced_order(config, partner, [(product, 1)])
                price = quote.amount_total
            else:
                price = None
            items.append({
                'id': product.id, 'product_id': product.id, 'name': product.display_name,
                'description': html2plaintext(product.description_ecommerce or product.description_sale or ''),
                'price': price, 'currency': config.currency_id.name,
                'category': product.pos_categ_ids[:1].name or _('Menu'),
                'image': self._product_image(product, 512), 'direct_add': self._can_add(product),
            })
        return {'items': items, 'next_offset': offset + 40 if len(products) > 40 else None}

    @http.route('/spx/mobile/v2/dine-in/cart', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_cart(self):
        website, partner = self._scope()
        return self._cart_data_v2(website, partner)[0]

    @http.route('/spx/mobile/v2/dine-in/cart/add', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_add(self, product_id, qty, basket_key=None):
        website, partner = self._scope()
        try:
            product_id, qty = positive_id(product_id), quantity(qty)
        except ValueError as error:
            raise UserError(str(error)) from error
        config = self._config(website, required=True)
        product = self._products(website, config).search(
            self._menu_domain(website, config) + [('id', '=', product_id)], limit=1)
        if not product or not self._can_add(product):
            raise UserError(_('Please order this item with our team.'))
        basket, created = self._basket(website, partner, lock=True)
        self._check_key(basket, basket_key, created)
        items = dict(basket.items or {})
        key = str(product_id)
        total_qty = items.get(key, {}).get('qty', 0) + qty
        if total_qty > 99 or (key not in items and len(items) >= 40):
            raise UserError(_('For larger orders, please speak to our team.'))
        items[key] = {'qty': total_qty, 'name': product.display_name}
        basket.write({'items': items, 'token': str(uuid4())})
        return self._cart_data_v2(website, partner, basket)[0]

    @http.route('/spx/mobile/v2/dine-in/cart/update', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_update(self, line_id, qty, basket_key):
        website, partner = self._scope()
        try:
            line_id, qty = positive_id(line_id), quantity(qty, allow_zero=True)
        except ValueError as error:
            raise UserError(str(error)) from error
        basket, created = self._basket(website, partner, lock=True)
        self._check_key(basket, basket_key)
        items = dict(basket.items or {})
        key = str(line_id)
        if key not in items:
            raise AccessError(_('This basket item is unavailable.'))
        if qty:
            items[key] = {**items[key], 'qty': qty}
        else:
            del items[key]
        basket.write({'items': items, 'token': str(uuid4())})
        return self._cart_data_v2(website, partner, basket)[0]

    @http.route('/spx/mobile/v2/dine-in/submit', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_submit(self, basket_key, quote):
        website, partner = self._scope()
        try:
            basket_key = mutation_id(basket_key)
            quote = mutation_id(quote)
        except ValueError as error:
            raise UserError(str(error)) from error
        basket, _created = self._basket(website, partner, lock=True)
        submissions = request.env['spx.mobile.submission'].sudo()
        previous = submissions.search(self._owner_domain(website, partner) + [('key', '=', basket_key)], limit=1)
        if previous:
            if previous.quote != quote:
                raise UserError(_('This basket was already submitted. Check Your orders before ordering again.'))
            return {'status': 'received', 'order': self._receipt(previous)}
        self._check_key(basket, basket_key)
        config = self._config(website, required=True)
        # Keep a session closure from racing order creation. A changed snapshot
        # is retried by Odoo, then the open-session check runs again.
        request.env.cr.execute('SELECT id FROM pos_config WHERE id = %s FOR SHARE', [config.id])
        config.invalidate_recordset()
        session = config.current_session_id
        if session:
            request.env.cr.execute('SELECT id FROM pos_session WHERE id = %s FOR SHARE', [session.id])
            session.invalidate_recordset()
        if not session or session.state != 'opened':
            raise UserError(_('We’re not accepting app orders right now. Please speak to our team.'))
        cart, values, line_values = self._cart_data_v2(website, partner, basket)
        if not cart['can_submit'] or cart['quote'] != quote:
            return {'status': 'changed', 'cart': cart}
        order_uuid = str(uuid4())
        values.update({
            'uuid': order_uuid, 'source': 'pos', 'table_id': False,
            'floating_order_name': _('App · %s', partner.name),
            'internal_note': _('Customer app order. Confirm the guest and table, then send to preparation.'),
            'payment_ids': [], 'to_invoice': False,
            'lines': [Command.create({**line, 'uuid': str(uuid4())}) for line in line_values],
        })
        native = request.env['pos.order'].sudo().with_company(website.company_id)
        native.sync_from_ui([values])
        order = native.search([('uuid', '=', order_uuid), ('partner_id', '=', partner.id),
                               ('company_id', '=', website.company_id.id), ('config_id', '=', config.id)], limit=1)
        if not order or order.state != 'draft' or order.payment_ids or order.table_id:
            raise UserError(_('Your order could not be submitted. Please speak to our team.'))
        # Re-evaluate native totals on the actual saved lines. Do not reprice or
        # touch any pre-existing staff bill. No _send_order or loyalty mutation.
        order._compute_prices()
        if config.currency_id.compare_amounts(order.amount_total, cart['total']):
            raise UserError(_('Prices changed while sending your order. Refresh and review your basket.'))
        receipt = {'name': order.pos_reference, 'date': self._date(order.date_order),
                   'total': order.amount_total, 'currency': order.currency_id.name, 'state': 'draft',
                   'submission_key': basket_key}
        submissions.create({'partner_id': partner.id, 'website_id': website.id,
                            'key': basket_key, 'quote': quote, 'order_id': order.id, 'receipt': receipt})
        basket.write({'items': {}, 'token': str(uuid4())})
        return {'status': 'received', 'order': receipt}

    @http.route('/spx/mobile/v2/dine-in/orders', type='jsonrpc', auth='user', website=True, methods=['POST'])
    def dine_orders(self):
        website, partner = self._scope()
        config = self._config(website)
        if not config:
            return []
        # Exact partner scope. Merged/shared bills belonging to someone else
        # are not exposed through the previous app submission's foreign key.
        orders = request.env['pos.order'].sudo().search([
            ('partner_id', '=', partner.id), ('company_id', '=', website.company_id.id),
            ('config_id', '=', config.id), ('state', 'in', ['draft', 'paid', 'done', 'cancel']),
        ], order='date_order desc, id desc', limit=40)
        return [{'name': o.pos_reference or o.name, 'date': self._date(o.date_order),
                 'total': o.amount_total, 'currency': o.currency_id.name, 'state': o.state} for o in orders]
