"""Repair legacy plain-text notes on orders submitted by this connector only."""
import json
import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def repair_app_order_notes(env):
    submissions = env['spx.mobile.submission'].search([('order_id', '!=', False)])
    repaired = 0
    for order in submissions.mapped('order_id'):
        note = order.internal_note
        if not note:
            continue
        try:
            json.loads(note)
        except json.JSONDecodeError:
            # Preserve the complete existing text, including any staff edits.
            # Do not change lines, preparation state, customer, payments or points.
            order.write({'internal_note': json.dumps([{'text': note, 'colorIndex': 0}])})
            repaired += 1
    return repaired


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    repaired = repair_app_order_notes(env)
    _logger.info('Jenny customer app: repaired internal-note format on %s app orders.', repaired)
