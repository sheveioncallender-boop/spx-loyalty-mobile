from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Existing submissions retain the exact native order relation. Never match
    # by customer or receipt text, and never touch unrelated POS records.
    orders = env['spx.mobile.submission'].search([]).mapped('order_id')
    orders._spx_repair_app_order_metadata()
