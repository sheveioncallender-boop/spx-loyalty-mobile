"""Persist Odoo's POS-calculated loyalty handoff until native payment completes.

No alternative earning rules or direct card/history writes. Only app-originated
orders participate; native confirm_coupon_programs remains the sole writer.
"""
from copy import deepcopy
import hashlib
import json
import logging
import math
from psycopg2 import errors

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    spx_loyalty_snapshot = fields.Json(copy=False, readonly=True,
                                      groups='point_of_sale.group_pos_user')
    spx_loyalty_finalized = fields.Boolean(copy=False, readonly=True,
                                         groups='point_of_sale.group_pos_user')

    def _spx_is_app_order(self):
        self.ensure_one()
        return bool(self.env['spx.mobile.submission'].sudo().search_count([
            ('order_id', '=', self.id),
        ]))

    def _spx_check_cashier(self):
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_('Only POS staff can prepare loyalty.'))
        self.check_access('write')
        if any(order.company_id not in self.env.companies for order in self):
            raise AccessError(_('This POS company is unavailable.'))

    def _spx_lock_loyalty(self):
        self.ensure_one()
        self.flush_recordset()
        self.env.cr.execute('SELECT id FROM pos_order WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()

    def _spx_loyalty_fingerprint(self):
        self.ensure_one()
        data = {
            'partner': self.partner_id.id, 'config': self.config_id.id,
            'company': self.company_id.id, 'currency': self.currency_id.id,
            'pricelist': self.pricelist_id.id, 'fiscal_position': self.fiscal_position_id.id,
            'total': self.amount_total,
            'lines': [{
                'uuid': line.uuid, 'product': line.product_id.id, 'qty': line.qty,
                'price': line.price_unit, 'discount': line.discount,
                'subtotal': line.price_subtotal, 'subtotal_incl': line.price_subtotal_incl,
                'taxes': sorted(line.tax_ids.ids), 'reward': line.reward_id.id,
                'coupon': line.coupon_id.id, 'cost': line.points_cost,
                'reward_code': line.reward_identifier_code,
            } for line in self.lines.sorted('id')],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _spx_recovery_programs(self):
        """Only unchanged automatic earning rules can recover an old plain bill."""
        self.ensure_one()
        if self.lines.filtered('is_reward_line'):
            return self.env['loyalty.program']
        programs = self.config_id._get_program_ids().filtered(
            lambda p: p.active and p.program_type == 'loyalty' and p.trigger == 'auto'
            and p.write_date <= self.date_order
            and all(rule.write_date <= self.date_order for rule in p.rule_ids)
        )
        return programs

    def spx_prepare_loyalty(self, coupon_data, recovery=False):
        """Authenticated cashier handoff; never a customer-provided points API."""
        self.ensure_one()
        self._spx_check_cashier()
        if not self._spx_is_app_order():
            return {'prepared': False}
        self._spx_lock_loyalty()
        if self.state == 'cancel' or not self.partner_id:
            return {'prepared': False}
        if not isinstance(coupon_data, dict):
            raise UserError(_('Invalid loyalty handoff.'))
        programs = self.config_id._get_program_ids().filtered(
            lambda p: p.active and p.program_type == 'loyalty'
        )
        paid = self.state in ('paid', 'done', 'invoiced')
        if paid:
            if not recovery or self.spx_loyalty_finalized:
                return {'prepared': False}
            programs &= self._spx_recovery_programs()
        accepted = {}
        for key, original in coupon_data.items():
            if not isinstance(original, dict):
                raise UserError(_('Invalid loyalty handoff.'))
            values = deepcopy(original)
            program = programs.filtered(lambda p: p.id == values.get('program_id'))
            if not program or values.get('partner_id') != self.partner_id.id:
                raise UserError(_('The loyalty handoff no longer matches this customer or program.'))
            try:
                card_id = int(key)
            except (TypeError, ValueError):
                raise UserError(_('Invalid loyalty card.')) from None
            for field in ('points', 'points_earned', 'points_spent'):
                value = values.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise UserError(_('Invalid loyalty points.'))
            if paid and (values['points_spent'] or values['points'] < 0):
                raise UserError(_('Historical reward spending requires staff review.'))
            if card_id > 0:
                card = self.env['loyalty.card'].browse(card_id).exists()
                if card.partner_id != self.partner_id or card.program_id != program:
                    raise UserError(_('The loyalty card does not belong to this bill.'))
            accepted[str(card_id)] = values
        self.write({'spx_loyalty_snapshot': {
            'fingerprint': self._spx_loyalty_fingerprint(), 'coupons': accepted,
        }})
        result = self._spx_finalize_loyalty() if paid else {}
        return {'prepared': True, 'result': result}

    def _spx_finalize_loyalty(self):
        self.ensure_one()
        self._spx_lock_loyalty()
        snapshot = self.spx_loyalty_snapshot
        if (not snapshot or self.state not in ('paid', 'done', 'invoiced')
                or not self.currency_id.is_zero(self.get_amount_unpaid())
                or snapshot['fingerprint'] != self._spx_loyalty_fingerprint()):
            return {}
        # Odoo handles existing cards, rule payloads, reward links, history and
        # duplicate suppression. Do not increment points or create history here.
        return self.confirm_coupon_programs(deepcopy(snapshot['coupons']))

    def confirm_coupon_programs(self, coupon_data):
        self.ensure_one()
        if not self._spx_is_app_order():
            return super().confirm_coupon_programs(coupon_data)
        self._spx_check_cashier()
        self._spx_lock_loyalty()
        if (self.state not in ('paid', 'done', 'invoiced')
                or not self.currency_id.is_zero(self.get_amount_unpaid())):
            raise UserError(_('Loyalty is confirmed only after full payment.'))
        result = super().confirm_coupon_programs(deepcopy(coupon_data))
        # A callback may have confirmed this order before the cashier receives
        # the paid-order notification. Native duplicate suppression is correct,
        # but returns no balances in that case. Refresh only cards already
        # recorded by native history for this order, without awarding again.
        histories = self.env['loyalty.history'].search([
            ('order_model', '=', self._name), ('order_id', '=', self.id),
            ('card_id.program_id.program_type', '=', 'loyalty'),
            ('card_id.partner_id', '=', self.partner_id.id),
        ])
        updated = {item['old_id'] for item in result['coupon_updates']}
        for key, values in coupon_data.items():
            card = histories.card_id.filtered(
                lambda c: c.program_id.id == values.get('program_id')
            )[:1]
            if card and int(key) not in updated:
                result['coupon_updates'].append({
                    'old_id': int(key), 'id': card.id, 'points': card.points,
                    'code': card.code, 'program_id': card.program_id.id,
                    'partner_id': card.partner_id.id,
                })
        # This row write also serializes a simultaneous browser confirmation and
        # bank callback under Odoo's transaction retry mechanism.
        self.write({'spx_loyalty_snapshot': False, 'spx_loyalty_finalized': True})
        return result

    def _process_saved_order(self, draft):
        result = super()._process_saved_order(draft)
        if not draft and self._spx_is_app_order():
            try:
                # A loyalty/communication failure must not undo Odoo's payment
                # records. Keep the snapshot for a later native POS confirmation.
                with self.env.cr.savepoint():
                    self._spx_finalize_loyalty()
            except (errors.SerializationFailure, errors.DeadlockDetected):
                raise  # Let Odoo retry the entire concurrent transaction.
            except Exception:
                _logger.exception('App POS loyalty confirmation deferred for order %s', self.id)
        return result

    @api.model
    def spx_loyalty_recovery_orders(self, config_id):
        """Resume old paid app bills when POS reconnects; no bill/payment writes."""
        self._spx_check_cashier()
        config = self.env['pos.config'].browse(config_id).exists()
        config.check_access('read')
        if not config or config.company_id not in self.env.companies:
            raise AccessError(_('This POS is unavailable.'))
        ids = self.env['spx.mobile.submission'].sudo().search([
            ('order_id.config_id', '=', config.id),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.spx_loyalty_finalized', '=', False),
        ]).mapped('order_id').ids
        orders = self.search([('id', 'in', ids)], order='id', limit=100)
        eligible = {}
        for order in orders:
            if (not order.partner_id or not order.currency_id.is_zero(order.get_amount_unpaid())
                    or not order.payment_ids.filtered('online_account_payment_id')):
                continue
            if self.env['loyalty.history'].search_count([
                ('order_model', '=', 'pos.order'), ('order_id', '=', order.id),
            ]):
                continue
            programs = order._spx_recovery_programs()
            if programs:
                eligible[order.id] = programs.ids
        return {
            'orders': self.read_pos_orders([('id', 'in', list(eligible))]) if eligible else {},
            'programs': eligible,
        }

