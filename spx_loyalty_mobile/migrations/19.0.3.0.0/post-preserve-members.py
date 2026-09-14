from odoo import api, SUPERUSER_ID
from odoo.addons.spx_loyalty_mobile.hooks import preserve_existing_members


def migrate(cr, version):
    preserve_existing_members(api.Environment(cr, SUPERUSER_ID, {}))
