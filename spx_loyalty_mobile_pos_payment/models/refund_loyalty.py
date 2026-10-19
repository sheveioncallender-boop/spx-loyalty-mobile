"""Reverse the recorded award after a native full refund of a plain app bill.

No payment/refund creation, earning-rule calculation or direct card/history writes.
Unsupported partial refunds and exchanges remain available in Odoo, but need
separate loyalty review rather than an invented points-allocation policy.
"""
import logging

from psycopg2 import errors

from odoo import _, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)
_PAID = ('paid', 'done', 'invoiced')


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def spx_reconcile_refund_loyalty(self):
        """Staff-only retry, deriving every point from native saved records."""
        self.ensure_one()
        self._spx_check_cashier()
        if self.state not in _PAID or not self.currency_id.is_zero(self.get_amount_unpaid()):
            return {'status': 'unpaid', 'card_ids': []}
        sources = self.lines.refunded_orderline_id.order_id
        if not sources.filtered(lambda order: order._spx_is_app_order()):
            return {'status': 'not_app_refund', 'card_ids': []}
        if len(sources) != 1:
            raise UserError(_('Loyalty for refunds from multiple bills requires review.'))
        source = sources
        source.check_access('read')
        source._spx_lock_loyalty()
        self._spx_lock_loyalty()
        if (source.state not in _PAID or not source.partner_id
                or self.partner_id != source.partner_id
                or self.company_id != source.company_id
                or self.currency_id != source.currency_id):
            raise UserError(_('The refund must retain the original customer, company and currency.'))
        # Exact full returns only: do not infer an allocation for partial returns,
        # reward spending, exchanges, or bills containing earlier returns.
        if (source.lines.filtered(lambda line: line.qty <= 0 or line.is_reward_line
                                  or line.refunded_orderline_id)
                or self.lines.filtered(lambda line: line.qty >= 0 or line.is_reward_line
                                       or not line.refunded_orderline_id)):
            raise UserError(_('Loyalty for exchanges or bills with rewards requires review.'))
        if set(self.lines.refunded_orderline_id.ids) != set(source.lines.ids):
            raise UserError(_('Partial-refund loyalty requires review; no points were changed.'))
        for line in source.lines:
            returned = -sum(self.lines.filtered(
                lambda refund_line: refund_line.refunded_orderline_id == line).mapped('qty'))
            if float_compare(returned, line.qty, precision_digits=6):
                raise UserError(_('Partial-refund loyalty requires review; no points were changed.'))

        History = self.env['loyalty.history']
        original = History.search([
            ('order_model', '=', 'pos.order'), ('order_id', '=', source.id),
            ('card_id.program_id.program_type', '=', 'loyalty'),
        ])
        cards = original.card_id
        if not cards:
            return {'status': 'no_award', 'card_ids': []}
        if any(card.partner_id != source.partner_id
               or (card.company_id and card.company_id != source.company_id) for card in cards):
            raise UserError(_('The original loyalty card requires review.'))
        # Card updates serialize concurrent returns under Odoo's transaction
        # retry mechanism, including when a source was read in an older snapshot.
        cards.flush_recordset()
        self.env.cr.execute('SELECT id FROM loyalty_card WHERE id IN %s ORDER BY id FOR UPDATE',
                            [tuple(cards.ids)])
        cards.invalidate_recordset()
        amounts = {card.id: sum(original.filtered(lambda h: h.card_id == card).mapped('issued'))
                   for card in cards}
        if any(amount <= 0 for amount in amounts.values()):
            raise UserError(_('The original loyalty award requires review.'))
        related_refunds = self.search([
            ('lines.refunded_orderline_id.order_id', '=', source.id),
            ('state', 'in', _PAID),
        ])
        history = History.search([
            ('order_model', '=', 'pos.order'), ('order_id', 'in', related_refunds.ids),
            ('card_id', 'in', cards.ids),
        ])
        if history:
            # Native history is the idempotency ledger. Never overwrite an
            # existing adjustment or subtract the original award a second time.
            if (len(history) == len(cards)
                    and all(h.order_id == self.id and h.used == 0
                            and h.issued == -amounts[h.card_id.id] for h in history)):
                return {'status': 'reversed', 'card_ids': cards.ids}
            raise UserError(_('This bill already has refund loyalty history; review it before adjusting points.'))
        coupons = {str(card.id): {
            'program_id': card.program_id.id, 'coupon_id': card.id,
            # Omit partner_id: keep the exact card from the original award;
            # do not let native customer lookup select another card.
            'points': -amounts[card.id], 'points_earned': -amounts[card.id],
            'points_spent': 0,
        } for card in cards}
        with self.env.cr.savepoint():
            self.confirm_coupon_programs(coupons)
            confirmed = History.search([
                ('order_model', '=', 'pos.order'), ('order_id', '=', self.id),
                ('card_id', 'in', cards.ids),
            ])
            if (len(confirmed) != len(cards)
                    or any(h.used or h.issued != -amounts[h.card_id.id] for h in confirmed)):
                raise UserError(_('Native loyalty confirmation could not reconcile this refund.'))
        return {'status': 'reversed', 'card_ids': cards.ids}

    def action_spx_reconcile_refund_loyalty(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(_('Only a POS manager can reconcile historical refund points.'))
        result = self.spx_reconcile_refund_loyalty()
        if result['status'] != 'reversed':
            raise UserError(_('No eligible paid app refund with a recorded loyalty award was found.'))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Refund loyalty reconciled'),
                       'message': _('The original earned points have been reversed once. No payments were changed.'),
                       'type': 'success', 'sticky': False},
        }

    def _process_saved_order(self, draft):
        result = super()._process_saved_order(draft)
        if not draft and self.lines.refunded_orderline_id:
            try:
                with self.env.cr.savepoint():
                    self.spx_reconcile_refund_loyalty()
            except (errors.SerializationFailure, errors.DeadlockDetected):
                raise
            except Exception:
                # Odoo has already performed its normal refund. A loyalty
                # problem must not undo it or request another monetary refund.
                _logger.exception('Refund loyalty review needed for POS order %s', self.id)
        return result
