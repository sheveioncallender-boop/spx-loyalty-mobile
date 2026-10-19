from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Repair display metadata on app bills paid through POS UI before this fix.
    orders = env['spx.mobile.submission'].search([]).mapped('order_id')
    orders._spx_repair_app_order_metadata()
